# -*- coding: utf-8 -*-

"""
Cloudformation Template Generation.
"""

import json

from troposphere_mate import (
    Template, Parameter, Ref, helper_fn_sub,
    ecr,
)

from ..devops.config_init import config

template = Template()

param_env_name = Parameter(
    "EnvironmentName",
    Type="String",
    Default=config.ECS_EXAMPLE_ENVIRONMENT_NAME.get_value()
)

template.add_parameter(param_env_name)

ecr_repo_life_cycle_policy = {
    "rules": [
        {
            "rulePriority": 1,
            "description": "keep untagged (historical) image for N days",
            "selection": {
                "tagStatus": "untagged",
                "countType": "sinceImagePushed",
                "countUnit": "days",
                "countNumber": 1
            },
            "action": {
                "type": "expire"
            }
        }
    ]
}

ecr_repo_webapp = ecr.Repository(
    "ECRRepoWebApp",
    RepositoryName=helper_fn_sub("{}-webapp", param_env_name),
    LifecyclePolicy=ecr.LifecyclePolicy(
        LifecyclePolicyText=json.dumps(ecr_repo_life_cycle_policy)
    )
)


template.create_resource_type_label()

# give all aws resource common tags
common_tags = {
    "EnvironmentName": Ref(param_env_name),
}
template.update_tags(common_tags)
