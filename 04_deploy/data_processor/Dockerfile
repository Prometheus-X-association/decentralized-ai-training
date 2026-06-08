FROM ghcr.io/alelevente/base_slim:latest
WORKDIR /data_processor
#COPY src/data_processor.py .
#COPY src/model.py .
#COPY dp_runner.sh .
COPY ./ ./
#RUN chmod +x dp_runner.sh
EXPOSE 8000
EXPOSE 5000
ENV mlflow_tracking_uri_internal=http://localhost:5000
#CMD ./dp_runner.sh
CMD [ "bash", "dp_runner.sh" ]
