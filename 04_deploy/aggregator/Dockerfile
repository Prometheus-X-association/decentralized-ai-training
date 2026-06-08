FROM ghcr.io/alelevente/base_slim:latest
WORKDIR /aggregator
#COPY src/aggregator.py .
#COPY src/model.py .
#COPY agg_runner.sh .
#COPY src/agg_algorithms.py .
#COPY cfg/mlflow_admin.json /cfg/mlflow_admin.json
COPY ./ ./
#RUN chmod +x agg_runner.sh
EXPOSE 8000
EXPOSE 5000
#if test_deploy: a random secret key
#ENV MLFLOW_FLASK_SERVER_SECRET_KEY="QlZzjbifUtn2bEGPl5OM0FZ8Je7BmI7SpqMgo6jsyNI"
#if test_deploy:
#ENV MLFLOW_BASIC_AUTH=true
ENV mlflow_tracking_uri_internal=http://localhost:5000
#CMD ./agg_runner.sh
CMD [ "bash", "agg_runner.sh" ]