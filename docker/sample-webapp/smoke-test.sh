#!/bin/bash

dir_here="$( cd "$(dirname "$0")" ; pwd -P )"
dir_project_root="${dir_here}"
dir_webapp_dockerfile="${dir_here}"

repo_name="sample-webapp"
tag_name="dev"
container_name="${repo_name}-smoke-test"

check_exit_status() {
    exit_status=$1
    if [ $exit_status != 0 ]
    then
        echo "FAILED!"
        docker container stop "${container_name}"
        exit $exit_status
    fi
}

docker run --rm -dt --name "${container_name}" -p 10001:80 "${repo_name}:${tag_name}"
sleep 10 # sleep 2 seconds wait web server become ready

echo "check if the web app successfully running locally"
curl "http://127.0.0.1:10001"
check_exit_status $?
echo ""
echo "yes"

# remove container if all success
docker container stop "${container_name}"
