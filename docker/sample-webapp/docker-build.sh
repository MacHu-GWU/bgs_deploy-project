#!/bin/bash
#
# This is a utility script allows you to build the image defined in the current
# directory.

dir_here="$( cd "$(dirname "$0")" ; pwd -P )"
dir_project_root="${dir_here}"
dir_webapp_dockerfile="${dir_here}"

source ${dir_project_root}/bin/py/python-env.sh

path_get_config_value_script="${dir_project_root}/config/get-config-value"

repo_name="sample-webapp"
tag_name="dev"

docker build --tag "${repo_name}:${tag_name}" --file "${dir_webapp_dockerfile}/Dockerfile" "${dir_project_root}"
docker image ls # list recently built image
docker image rm "${repo_name}:${tag_name}" # remove recently built image
