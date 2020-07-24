#!/bin/bash

dir_here="$( cd "$(dirname "$0")" ; pwd -P )"

export FLASK_APP=${dir_here}/app.py
flask run --host=127.0.0.1

