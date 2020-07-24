# -*- coding: utf-8 -*-

from flask import Flask, request

__version__ = "0.0.1"
__service_name__ = "sample webapp"

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == "GET":
        return "Hello World, this is service: '{service_name}', this is version: '{version}'".format(
            service_name=__service_name__,
            version=__version__,
        )
    elif request.method == "POST":
        return "Hello {name}, this is service: '{service_name}', this is version: '{version}'".format(
            name=request.form["name"],
            service_name=__service_name__,
            version=__version__,
        )
