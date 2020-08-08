# -*- coding: utf-8 -*-

import csv
import os

from attrs_mate import attr
from constant2 import Constant


class ConstantMixIn(Constant):
    @classmethod
    def validate(cls, value, param_name):
        if value not in cls.Values():
            msg = (
                "'{value}' is not value for parameter '{param_name}', "
                "valid values are: {valid_values}"
            ).format(
                value=value,
                param_name=param_name,
                valid_values=cls.Values()
            )
            raise ValueError(msg)


class DeploymentOptions(Constant, ConstantMixIn):
    do_nothing = "do_nothing"
    deploy_to_staging = "deploy_to_staging"
    destroy_staging = "destroy_staging"
    deploy_to_active = "deploy_to_active"
    roll_back_to_previous = "roll_back_to_previous"


class DeploymentLogicIds(Constant, ConstantMixIn):
    a = "a"
    b = "b"
    c = "c"


class DeploymentEnvNames(Constant, ConstantMixIn):
    active = "active"
    inactive = "inactive"
    staging = "staging"


fact_table_tsv = os.path.join(os.path.dirname(__file__), "fact-table.tsv")
fact_table_dict = dict()
"""
{
    "do_nothing-0-0-0": {
        "is_valid": True | False,
        "future_active": True | False,
        "future_inactive": True | False,
        "future_staging": True | False,
    },
    ...
}
"""

IS_VALID = "is_valid"

with open(fact_table_tsv, newline="") as csvfile:
    csv_reader = csv.reader(csvfile, delimiter="\t")
    next(csv_reader)
    for row in csv_reader:
        key = "-".join(row[:4])
        is_valid = bool(int(row[4]))
        future_active = bool(int(row[5]))
        future_inactive = bool(int(row[6]))
        future_staging = bool(int(row[7]))
        fact_table_dict[key] = {
            IS_VALID: is_valid,
            DeploymentEnvNames.active: future_active,
            DeploymentEnvNames.inactive: future_inactive,
            DeploymentEnvNames.staging: future_staging,
        }

@attr.s
class BlueGreenStageDeployment(object):
    @property
    def current_active_logic_id(self):
        """

        :rtype: str
        """
        raise NotImplementedError

    @property
    def current_inactive_logic_id(self):
        """

        :rtype: str
        """
        raise NotImplementedError

    @property
    def current_staging_logic_id(self):
        """

        :rtype: str
        """
        raise NotImplementedError

    def _has_active_inactive_staging(self, bgs_logic_id):
        """
        Internal implementation method. Returns if active, or inactive, or
        staging resources exists.

        :param bgs_logic_id: the logic_id for current active, or inactive,
            or staging.
        :type bgs_logic_id: str

        :rtype: bool
        """
        if isinstance(bgs_logic_id, str):
            return True
        else:
            return False

    def has_active(self):
        """
        Does resources for active environment exists?

        :rtype: bool
        """
        return self._has_active_inactive_staging(self.current_active_logic_id)

    def has_inactive(self):
        """
        Does resources for inactive environment exists?

        :rtype: bool
        """
        return self._has_active_inactive_staging(self.current_inactive_logic_id)

    def has_staging(self):
        """
        Does resources for staging environment exists?

        :rtype: bool
        """
        return self._has_active_inactive_staging(self.current_staging_logic_id)

    def find_which_logic_id_should_use_for_staging(self):
        """
        Find out when deploying new release to staging, which logic id
        should be used.

        Since we only have three logic id: a, b, c. Just check which are
        already taken by active and inactive, then just pick one logic id from
        what's left. If there are multiple logic ids are available for staging,
        use the first one based on alphabetic order.

        :rtype: str
        """
        available_logic_id_list = list(DeploymentLogicIds.Values())
        available_logic_id_list.sort()
        if self.current_active_logic_id in available_logic_id_list:
            available_logic_id_list.remove(self.current_active_logic_id)
        if self.current_inactive_logic_id in available_logic_id_list:
            available_logic_id_list.remove(self.current_inactive_logic_id)
        return available_logic_id_list[0]

    def should_create_bgs_resource(self, deployment_option, bgd_env_name):
        """
        Returns a boolean value indicates whether should create infrastructure
        as code resources for this specific stage.

        :type deployment_option: str
        :type bgd_env_name: str

        :rtype: bool
        """
        DeploymentOptions.validate(
            value=deployment_option, param_name="deployment_option"
        )
        DeploymentEnvNames.validate(
            value=bgd_env_name, param_name="bgd_env_name"
        )
        key = "{}-{}-{}-{}".format(
            deployment_option,
            self.has_active(),
            self.has_inactive(),
            self.has_staging(),
        )
        if key not in fact_table_dict:
            raise KeyError

        if fact_table_dict[key][IS_VALID]:
            return fact_table_dict[key][bgd_env_name]
        else:
            d = {
                0: "not exists",
                1: "exists",
            }
            msg = (
                "System state is invalid: "
                "active = {}, "
                "inactive = {}, "
                "staging = {}"
            ).format(
                d[int(self.has_active())],
                d[int(self.has_inactive())],
                d[int(self.has_staging())],
            )
            raise Exception(msg)
