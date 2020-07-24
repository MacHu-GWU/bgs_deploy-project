#!/bin/bash
#
# NOTE:
#
# This script should be manually invoked from local, its just for testing
# of ``build-api-service-docker-image.sh`` shell script.

if [ -n "${BASH_SOURCE}" ]
then
    dir_here="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
else
    dir_here="$( cd "$(dirname "$0")" ; pwd -P )"
fi

bash ${dir_here}/build-docker-image.sh prod sample-webapp bgs-deploy-prod-ecs-example-webapp
