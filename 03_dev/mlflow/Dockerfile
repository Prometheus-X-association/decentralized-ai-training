FROM python:3.12

RUN pip install mlflow[auth]

EXPOSE 5555

ENV MLFLOW_FLASK_SERVER_SECRET_KEY="my-secret-key"

CMD mlflow server --host 0.0.0.0 --port 5555 --app-name basic-auth
