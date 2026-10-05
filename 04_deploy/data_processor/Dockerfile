FROM ghcr.io/alelevente/base_slim:latest
WORKDIR /data_processor
#COPY src/data_processor.py .
#COPY src/model.py .
#COPY dp_runner.sh .
COPY ./ ./
#RUN chmod +x dp_runner.sh
RUN pip3 install --no-cache-dir -U mlflow-skinny
EXPOSE 8000
#CMD ./dp_runner.sh
CMD [ "bash", "dp_runner.sh" ]
