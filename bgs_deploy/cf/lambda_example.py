# -*- coding: utf-8 -*-

"""
Cloudformation Template Generation.
"""

import json

from troposphere_mate import (
    Template, Parameter, Ref, helper_fn_sub,
    iam, awslambda, canned,
)

from ..devops.config_init import config

template = Template()

param_env_name = Parameter(
    "EnvironmentName",
    Type="String",
    Default=config.ECS_EXAMPLE_ENVIRONMENT_NAME.get_value()
)

template.add_parameter(param_env_name)

iam_role_lambda_exec = iam.Role(
    "IamForLambda",
    RoleName=helper_fn_sub("{}-lambda-exec-role", param_env_name),
    AssumeRolePolicyDocument=canned.iam.create_assume_role_policy_document([
        canned.iam.AWSServiceName.aws_Lambda,
    ]),
    ManagedPolicyArns=[
        canned.iam.AWSManagedPolicyArn.awsLambdaBasicExecutionRole,
    ]
)

template.create_resource_type_label()

# give all aws resource common tags
common_tags = {
    "EnvironmentName": Ref(param_env_name),
}
template.update_tags(common_tags)
