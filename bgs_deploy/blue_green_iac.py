# -*- coding: utf-8 -*-

import json
import re

from attrs_mate import attr
from constant2 import Constant


@attr.s
class BlueGreenDeployment(object):
    boto_ses = attr.ib()
    tf_s3_bucket = attr.ib()
    tf_s3_key = attr.ib()

    _tf_state_data_cache = None

    def _get_tf_state_data(self):
        s3_client = self.boto_ses.client("s3")
        try:
            res = s3_client.get_object(Bucket=self.tf_s3_bucket, Key=self.tf_s3_key)
        except:
            return {"resources": []}
        try:
            state_data = json.loads(res["Body"].read())
        except:
            return {"resources": []}
        return state_data

    @property
    def tf_state_data(self):
        if self._tf_state_data_cache is None:
            self._tf_state_data_cache = self._get_tf_state_data()
        return self._tf_state_data_cache


sha256_pattern = re.compile("[A-Fa-f0-9]{64}")


def validate_sha256_str(value):
    assert len(value) == 64
    assert re.match(sha256_pattern, value) is not None


task_definition_arn_pattern = re.compile(
    "arn:aws:ecs:[A-Za-z0-9\-_]{7,32}:[0-9]{12}:task-definition/[A-Za-z0-9\-_]{1,128}:[0-9]{1,4}")


def validate_task_definition_arn(value):
    assert re.match(task_definition_arn_pattern, value) is not None


@attr.s
class BlueGreenECSDeployment(BlueGreenDeployment):
    service_name = attr.ib()
    deployment_option = attr.ib()
    docker_image_digest = attr.ib(default=None)
    task_definition_arn = attr.ib(default=None)

    @docker_image_digest.validator
    def check_docker_image_digest(self, attribute, value):
        if bool(value):
            validate_sha256_str(value)

    @task_definition_arn.validator
    def check_task_definition_arn(self, attribute, value):
        if bool(value):
            validate_task_definition_arn(value)

    def _validate_parameters(self):
        # You should never specify docker_image_digest and task_definition_arn all together
        if bool(self.docker_image_digest) and bool(self.task_definition_arn):
            msg = "You can not specify both docker_image_digest and task_definition_arn"
            raise ValueError(msg)

        if self.deployment_option == self.DeploymentOptions.do_nothing:
            pass

        # when deploy-to-staging,
        # you have to specify exact one of docker_image_digest or task_definition_arn
        elif self.deployment_option == self.DeploymentOptions.deploy_to_staging:
            if not (bool(self.docker_image_digest) or bool(self.task_definition_arn)):
                msg = (
                    f"for deployment option '{self.DeploymentOptions.deploy_to_staging}', "
                    f"You have to specify exactly one of the"
                    f"{self.DeploymentParameters.docker_image_digest} "
                    f"or {self.DeploymentParameters.task_definition_arn}"
                )
                raise ValueError(msg)
        # when destroy-staging, deploy-to-active, or roll-back-to-previous,
        # you should not specify any of docker_image_digest or task_definition_arn
        elif self.deployment_option in [
            self.DeploymentOptions.destroy_staging,
            self.DeploymentOptions.deploy_to_active,
            self.DeploymentOptions.roll_back_to_previous,
        ]:
            if bool(self.docker_image_digest) or bool(self.task_definition_arn):
                msg = (
                    f"for deployment option "
                    f"'{self.DeploymentOptions.destroy_staging}' or "
                    f"'{self.DeploymentOptions.deploy_to_active}' or "
                    f"'{self.DeploymentOptions.roll_back_to_previous}', "
                    "You cannot specify any of "
                    f"{self.DeploymentParameters.docker_image_digest}"
                    f"and {self.DeploymentParameters.task_definition_arn}!"
                )
                raise ValueError(msg)
        else:
            raise ValueError(f"invalid deployment_option: '{self.deployment_option}'")

        if self.deployment_option == self.DeploymentOptions.deploy_to_active:
            if not bool(self.staging_logic_id):
                raise ValueError("You cannot deploy to active because there is nothing in staging.")

        if self.deployment_option == self.DeploymentOptions.roll_back_to_previous:
            if not (bool(self.active_logic_id) and bool(self.inactive_logic_id)):
                raise ValueError("You cannot roll back to previous because you don't have both active and inactive deployed.")

    def __attrs_post_init__(self):
        self._validate_parameters()

    class DeploymentOptions(Constant):
        do_nothing = "do_nothing"
        deploy_to_staging = "deploy_to_staging"
        destroy_staging = "destroy_staging"
        deploy_to_active = "deploy_to_active"
        roll_back_to_previous = "roll_back_to_previous"

    class DeploymentParameters(Constant):
        docker_image_digest = "docker_image_digest"
        task_definition_arn = "task_definition_arn"
        task_definition_arg = "task_definition_arg"

    class DeploymentLogicIds(Constant):
        a = "a"
        b = "b"
        c = "c"

    class DeploymentStages(Constant):
        active = "active"
        inactive = "inactive"
        staging = "staging"

    _blue_green_state_data_cache = None

    def _initial_blue_green_state_data(self):
        return {
            "logic_id": {
                self.DeploymentLogicIds.a: {
                    self.DeploymentParameters.docker_image_digest: None,
                    self.DeploymentParameters.task_definition_arn: None,
                    self.DeploymentParameters.task_definition_arg: None,
                },
                self.DeploymentLogicIds.b: {
                    self.DeploymentParameters.docker_image_digest: None,
                    self.DeploymentParameters.task_definition_arn: None,
                    self.DeploymentParameters.task_definition_arg: None,
                },
                self.DeploymentLogicIds.c: {
                    self.DeploymentParameters.docker_image_digest: None,
                    self.DeploymentParameters.task_definition_arn: None,
                    self.DeploymentParameters.task_definition_arg: None,
                }
            },
            "blue_green_stage": {
                self.DeploymentStages.active: {
                    "logic_id": None
                },
                self.DeploymentStages.inactive: {
                    "logic_id": None
                },
                self.DeploymentStages.staging: {
                    "logic_id": None
                },
            },
        }

    def _get_blue_green_state_data(self):
        state_data = self._initial_blue_green_state_data()
        for resource_data in self.tf_state_data["resources"]:
            if resource_data["type"] == "aws_ecs_task_definition" \
                    and resource_data["name"].startswith(self.service_name):
                logic_id = resource_data["name"].replace(f"{self.service_name}_", "")
                # get docker_image_digest
                docker_image_uri = json.loads(
                    resource_data["instances"][0]["attributes"]["container_definitions"]
                )[0]["image"]
                docker_image_digest = docker_image_uri.split(":")[-1]
                state_data["logic_id"][logic_id][self.DeploymentParameters.docker_image_digest] = docker_image_digest
                # get task_definition_arn
                task_definition_arn = resource_data["instances"][0]["attributes"]["arn"]
                state_data["logic_id"][logic_id][self.DeploymentParameters.task_definition_arn] = task_definition_arn

            if resource_data["type"] == "aws_ecs_service" \
                    and resource_data["name"].startswith(self.service_name):
                logic_id = resource_data["name"].replace(f"{self.service_name}_", "")
                # get task_definition_arg
                task_definition_arg = resource_data["instances"][0]["attributes"]["task_definition"]
                state_data["logic_id"][logic_id][self.DeploymentParameters.task_definition_arg] = task_definition_arg

            if resource_data["type"] == "aws_lb_listener" \
                    and resource_data["name"].startswith(self.service_name):
                blue_green_stage_name = resource_data["name"].replace(f"{self.service_name}_", "")
                logic_id = None
                for resource_type_name in resource_data["instances"][0]["depends_on"]:
                    if resource_type_name.startswith("aws_lb_target_group"):
                        logic_id = resource_type_name.split("_")[-1]
                    state_data["blue_green_stage"][blue_green_stage_name]["logic_id"] = logic_id
        return state_data

    @property
    def blue_green_state_data(self):
        if self._blue_green_state_data_cache is None:
            self._blue_green_state_data_cache = self._get_blue_green_state_data()
        return self._blue_green_state_data_cache

    @property
    def logic_a_docker_image_digest(self):
        return self.blue_green_state_data["logic_id"][self.DeploymentLogicIds.a][
            self.DeploymentParameters.docker_image_digest]

    @property
    def logic_a_task_definition_arn(self):
        return self.blue_green_state_data["logic_id"][self.DeploymentLogicIds.a][
            self.DeploymentParameters.task_definition_arn]

    @property
    def logic_b_docker_image_digest(self):
        return self.blue_green_state_data["logic_id"][self.DeploymentLogicIds.b][
            self.DeploymentParameters.docker_image_digest]

    @property
    def logic_b_task_definition_arn(self):
        return self.blue_green_state_data["logic_id"][self.DeploymentLogicIds.b][
            self.DeploymentParameters.task_definition_arn]

    @property
    def logic_c_docker_image_digest(self):
        return self.blue_green_state_data["logic_id"][self.DeploymentLogicIds.c][
            self.DeploymentParameters.docker_image_digest]

    @property
    def logic_c_task_definition_arn(self):
        return self.blue_green_state_data["logic_id"][self.DeploymentLogicIds.c][
            self.DeploymentParameters.task_definition_arn]

    @property
    def active_logic_id(self):
        return self.blue_green_state_data["blue_green_stage"][self.DeploymentStages.active]["logic_id"]

    @property
    def inactive_logic_id(self):
        return self.blue_green_state_data["blue_green_stage"][self.DeploymentStages.inactive]["logic_id"]

    @property
    def staging_logic_id(self):
        return self.blue_green_state_data["blue_green_stage"][self.DeploymentStages.staging]["logic_id"]

    def find_which_logic_id_should_use_for_staging(self):
        """
        Find out when deploying new release to staging, which logic id should be used.

        Since we only have three logic id: a, b, c. Just check which are
        already taken by active and inactive, then just pick one logic id from
        what's left.

        :rtype: str
        """
        available_logic_id_list = list(self.DeploymentLogicIds.Values())
        available_logic_id_list.sort()
        if self.active_logic_id in available_logic_id_list:
            available_logic_id_list.remove(self.active_logic_id)
        if self.inactive_logic_id in available_logic_id_list:
            available_logic_id_list.remove(self.inactive_logic_id)
        return available_logic_id_list[0]

    def is_docker_image_digest_deployment_type(self):
        """
        It returns whether it is docker_image_digest type.

        For ``deploy_to_staging``, there are only two deployment types:

        1. docker_image_digest, create a new task definition using specific
            docker image, and launch a task based on this new task definition.
            this is usually for new version release.
        2. task_definition_arn, use existing task definition. this is usually
            for rolling back to historical version.

        :rtype: bool
        """
        if self.docker_image_digest is not None:
            return True
        else:
            return False

    def get_future_logic_id_specified_config_value(self, logic_id, parameter_name):
        """
        For example, if ecs service name is helpdesk.
        ``logic_id`` = a, ``parameter_name`` = docker_image_digest

        Then this method returns the config value for
        ``HELPDESK_LOGIC_A_DOCKER_IMAGE_DIGEST``.

        Then jinja2 template will render terraform script based on these config
        value.

        :type logic_id: str
        :param logic_id: a | b | c

        :type parameter_name: str
        :param parameter_name:

        :rtype:
        """
        if logic_id not in self.DeploymentLogicIds.Values():
            raise ValueError
        if parameter_name not in self.DeploymentParameters.Values():
            raise ValueError

        if parameter_name == self.DeploymentParameters.docker_image_digest:
            parameter_value = self.docker_image_digest
        elif parameter_name == self.DeploymentParameters.task_definition_arn:
            parameter_value = self.task_definition_arn
        elif parameter_name == self.DeploymentParameters.task_definition_arg:
            if self.is_docker_image_digest_deployment_type():
                parameter_value = f"${{aws_ecs_task_definition.{self.service_name}_{logic_id}.arn}}"
            else:
                parameter_value = self.task_definition_arn
        else:
            raise TypeError

        existing_value = self.blue_green_state_data["logic_id"][logic_id][parameter_name]
        staging_logic_id = self.find_which_logic_id_should_use_for_staging()

        # When do_nothing, deploy_to_active, roll_back_to_previous
        #   it won't change any existing resources for logic group a, b, c
        #   it only changes the blue_green_stage specified resources
        #   in ECS case, it is load balancer listener
        if self.deployment_option in [
            self.DeploymentOptions.do_nothing,
            self.DeploymentOptions.deploy_to_active,
            self.DeploymentOptions.roll_back_to_previous,
        ]:
            return existing_value
        # When deploy_to_staging, we are deploy new resources to staging
        #   first need to find out what logic_id could be used for staging deployment
        #   if the current logic_id is the staging logic_id, then take the value
        #   from docker_image_digest or task_definition_arn
        #   otherwise, it is active or inactive stage,
        #   then use the existing value and remains it unchanged
        elif self.deployment_option == self.DeploymentOptions.deploy_to_staging:
            if logic_id == staging_logic_id:
                return parameter_value
            else:
                return existing_value
        # When destroy_staging
        # if logic_id match current staging logic id, set None for all config value.
        # i.e. remove tf resources
        elif self.deployment_option == self.DeploymentOptions.destroy_staging:
            if logic_id == staging_logic_id:
                return None
            else:
                return existing_value

    def get_future_blue_green_stage_specified_logic_id(self, blue_green_stage):
        """
        Returns a logic id indicates that for this specific
        active/inactive/staging blue green stage, which logic id should be use.

        :type blue_green_stage: str
        :param blue_green_stage: active | inactive | staging

        :rtype: str
        """
        staging_logic_id = self.find_which_logic_id_should_use_for_staging()
        existing_logic_id = self.blue_green_state_data["blue_green_stage"][blue_green_stage]["logic_id"]
        # When doing do_nothing
        #   just use previous logic id
        if self.deployment_option == self.DeploymentOptions.do_nothing:
            return existing_logic_id
        # When doing deploy_to_staging
        #   if it is staging, use the logic id derived from :meth:`find_which_logic_id_should_use_for_staging`
        #   if it is not staging, just use previous logic id
        elif self.deployment_option == self.DeploymentOptions.deploy_to_staging:
            if blue_green_stage == self.DeploymentStages.staging:
                return staging_logic_id
            else:
                return existing_logic_id
        # When doing destroy_staging:
        #   if it is staging, no logic_id will be used for this stage
        #   if it is not staging, just use previous logic id
        elif self.deployment_option == self.DeploymentOptions.destroy_staging:
            if blue_green_stage == self.DeploymentStages.staging:
                return None
            else:
                return existing_logic_id
        # When doing deploy_to_active
        #   previous staging becomes future active
        #   previous active becomes future inactive
        #   previous inactive becomes future staging
        elif self.deployment_option == self.DeploymentOptions.deploy_to_active:
            if blue_green_stage == self.DeploymentStages.active:
                return self.staging_logic_id
            elif blue_green_stage == self.DeploymentStages.inactive:
                return self.active_logic_id
            elif blue_green_stage == self.DeploymentStages.staging:
                return self.inactive_logic_id
        # When doing roll_back_to_previous
        #   just swap active and inactive
        elif self.deployment_option == self.DeploymentOptions.roll_back_to_previous:
            if blue_green_stage == self.DeploymentStages.active:
                return self.inactive_logic_id
            elif blue_green_stage == self.DeploymentStages.inactive:
                return self.active_logic_id
            elif blue_green_stage == self.DeploymentStages.staging:
                return self.staging_logic_id

    def should_create_logic_id_specified_resource(self, logic_id):
        """
        Returns a boolean value indicate that whether should create bunch of
        terraform resources for this specific logic_id. For ecs service,
        they are ``aws_ecs_task_definition``, ``aws_lb_target_group``,
        ``aws_ecs_service``.

        :rtype: bool
        """
        if logic_id not in self.DeploymentLogicIds.Values():
            raise ValueError

        existing_docker_image_digest = self.blue_green_state_data["logic_id"][logic_id][
            self.DeploymentParameters.docker_image_digest]
        existing_task_definition_arn = self.blue_green_state_data["logic_id"][logic_id][
            self.DeploymentParameters.task_definition_arn]
        is_exists = (bool(existing_docker_image_digest) or bool(existing_task_definition_arn))
        staging_logic_id = self.find_which_logic_id_should_use_for_staging()

        # for these options, we are not going to change any logic id specified
        # resources
        if self.deployment_option in [
            self.DeploymentOptions.do_nothing,
            self.DeploymentOptions.deploy_to_active,
            self.DeploymentOptions.roll_back_to_previous,
        ]:
            return is_exists
        # if deploy_to_staging, and this logic id is for staging
        # of course we should create resources for it
        elif self.deployment_option == self.DeploymentOptions.deploy_to_staging:
            if logic_id == staging_logic_id:
                return True
            else:
                return is_exists
        # if destroy_staging, and this logic id is for staging
        # of course we should NOT create resources for it
        elif self.deployment_option == self.DeploymentOptions.destroy_staging:
            if logic_id == staging_logic_id:
                return False
            else:
                return is_exists
        else:
            raise ValueError

    def should_create_blue_green_stage_specified_resource(self, blue_green_stage):
        """
        Returns a boolean value indicates whether should create bunch of
        terraform resources for this specific stage. For ecs service,
        it is ``aws_lb_listener``.

        :type blue_green_stage: str

        :rtype: bool
        """
        if blue_green_stage not in self.DeploymentStages.Values():
            raise ValueError

        existing_logic_id = self.blue_green_state_data["blue_green_stage"][blue_green_stage]["logic_id"]

        # When do_nothing
        #   if there is an existing logic id in use for this stage, then create
        if self.deployment_option == self.DeploymentOptions.do_nothing:
            return bool(existing_logic_id)
        # When deploy_to_staging:
        #   if it is staging, we create anyway
        #   for other blue_green_stage, if there is an existing logic id in use,
        #   then create
        elif self.deployment_option == self.DeploymentOptions.deploy_to_staging:
            if blue_green_stage == self.DeploymentStages.staging:
                return True
            else:
                return bool(existing_logic_id)
        # When destroy_staging
        #   if it is staging, we won't create it anyway
        elif self.deployment_option == self.DeploymentOptions.destroy_staging:
            if blue_green_stage == self.DeploymentStages.staging:
                return False
            else:
                return existing_logic_id
        # When deploy_to_active
        #   if it is active, we create anyway
        #   if it is inactive, if previous active exists, then create it
        #   if it is staging, if previous inactive exists, then create it
        elif self.deployment_option == self.DeploymentOptions.deploy_to_active:
            if blue_green_stage == self.DeploymentStages.active:
                return True
            elif blue_green_stage == self.DeploymentStages.inactive:
                return bool(self.active_logic_id)
            elif blue_green_stage == self.DeploymentStages.staging:
                return bool(self.inactive_logic_id)
            else:
                raise ValueError

        elif self.deployment_option == self.DeploymentOptions.roll_back_to_previous:
            if blue_green_stage == self.DeploymentStages.staging:
                return bool(self.staging_logic_id)
            else:
                return True
        else:
            raise ValueError
