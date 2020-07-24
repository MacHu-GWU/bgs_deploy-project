#!/bin/bash
#
# an automation scripts build and push docker image to ECR.
#
# Usage:
#
#   $ bash build-docker-image.sh ${STAGE} ${SERVICE_NAME} ${ECR_REPO_NAME}
#   $ bash build-docker-image.sh dev sample-webapp
#
# docker image will be pushed to ``${PROJECT_NAME}-prod-${SERVICE_NAME}`` ecr repo
# image tag will be ``${STAGE}-${VERSION}``, the version will be read from the
# ``version.txt`` file.
#
# Example, it pulls codes from https://github.cms.gov/IDM/idm-helpdesk and
# build the docker image, then push to AWS ECR:
#
#   build-docker-image.sh dev sample-webapp


if [ -n "${BASH_SOURCE}" ]; then
    dir_here="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
else
    dir_here="$( cd "$(dirname "$0")" ; pwd -P )"
fi
dir_project_root=$(dirname "${dir_here}")
get_config_value_bin_tool="${dir_project_root}/config/get-config-value"
read_config_value_bin_tool="${dir_project_root}/config/read-config-value"

source ${dir_project_root}/bin/py/python-env.sh

stage="$1"
service_name="$2"
ecr_repo_name="$3"

# initiate configs
bash ${dir_project_root}/config/switch-and-init.sh ${stage}

# if local runtime, set AWS_PROFILE environment
path_config_shared_file="${dir_project_root}/config/00-config-shared.json"
aws_cli_profile_arg="--profile $(${bin_python} ${read_config_value_bin_tool} ${path_config_shared_file} "AWS_PROFILE")"

# retrieve some dynamic value from config
aws_region="$(${bin_python} ${get_config_value_bin_tool} AWS_REGION)"
aws_account_id="$(${bin_python} ${get_config_value_bin_tool} AWS_ACCOUNT_ID)"
ecr_uri="${aws_account_id}.dkr.ecr.${aws_region}.amazonaws.com"
idm_service_git_repo_dir="${dir_project_root}/docker/${service_name}"

docker_app_version="$(cat ${dir_project_root}/docker/${service_name}/version.txt)"
img_tag_name="${stage}-${docker_app_version}" # tag name naming convention
img_identifier_local="${ecr_repo_name}:${img_tag_name}"
img_identifier_remote="${ecr_uri}/${ecr_repo_name}:${img_tag_name}"

# build image
echo "[INFO] execute: docker build"
docker build \
    --no-cache \
    --build-arg STAGE=${stage} \
    -t "${img_identifier_local}" \
    -f "${idm_service_git_repo_dir}/Dockerfile" \
    "${idm_service_git_repo_dir}"

# tag image
echo "[INFO] execute: docker tag ${img_identifier_local} ${img_identifier_remote}"
docker tag ${img_identifier_local} ${img_identifier_remote}

# aws ecr login
echo "[INFO] execute: aws ecr get-login ..."
aws ecr get-login --no-include-email --region ${aws_region} ${aws_cli_profile_arg} | awk '{printf $6}' | docker login -u AWS ${ecr_uri} --password-stdin

# docker push
echo "[INFO] execute: docker push ${img_identifier_remote}"
docker push ${img_identifier_remote}
