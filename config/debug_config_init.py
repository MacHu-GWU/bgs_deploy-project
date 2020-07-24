# -*- coding: utf-8 -*-

"""
This is a helper script allows developer to invoke the idm_devops.devops.config_init.py
module quickly, debug any potential bugs.
"""

from bgs_deploy.devops.config_init import config

_ = config

print(config.to_json())
