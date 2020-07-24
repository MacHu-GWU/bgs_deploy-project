FROM python:3.6.2-slim
COPY ./ /var/app
RUN pip install -r /var/app/requirements.txt
ENV FLASK_APP="/var/app/app.py"
ENV FLASK_RUN_HOST="0.0.0.0"
ENV FLASK_RUN_PORT="80"
ENTRYPOINT [ "flask", "run"]
