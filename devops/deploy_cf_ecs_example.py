# -*- coding: utf-8 -*-

"""
This is an example about how to deploy CloudFormation and integrate it with
your DevOps automation scripts.

The CloudFormation template will be generated from a python script that taking
all configurations and smartly decide which AWS resource and the naming convention
should be created. You can extend it by changing the
``./bgs_deploy/cf/__init__.py`` file.

``troposphere_mate`` allows you to deploy your CloudFormation stack to AWS
from Python.
"""

import boto3
from bgs_deploy.cf import ecs_example
from troposphere_mate import StackManager

config = ecs_example.config
ecs_example.template.add_resource(ecs_example.ecr_repo_webapp)

boto_ses = boto3.session.Session(
    profile_name=config.AWS_PROFILE_FOR_BOTO3.get_value(),
    region_name=config.AWS_REGION.get_value(),
)

sm = StackManager(boto_ses=boto_ses, cft_bucket=ecs_example.config.S3_BUCKET_FOR_DEPLOY.get_value())

sm.deploy(
    template=ecs_example.template,
    stack_name=config.ECS_EXAMPLE_ENVIRONMENT_NAME.get_value(),
    stack_parameters={
        ecs_example.param_env_name.title: config.ECS_EXAMPLE_ENVIRONMENT_NAME.get_value(),
    },
    include_iam=True
)
