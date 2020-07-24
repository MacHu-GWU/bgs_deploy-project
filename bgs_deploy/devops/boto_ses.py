# -*- coding: utf-8 -*-

import boto3
from .config_init import config

boto_ses = boto3.session.Session(
    profile_name=config.AWS_PROFILE_FOR_BOTO3.get_value(),
    region_name=config.AWS_REGION.get_value(),
)