FROM ghcr.io/alelevente/base_alpine:latest
WORKDIR /data_provider
#COPY src/data_provider.py .
#COPY dp_runner.sh .
#COPY data/ /data/
COPY ./ ./
#RUN chmod +x dp_runner.sh
EXPOSE 8000
ENV DATA_PATH=/data_provider/data
#CMD ./dp_runner.sh
#CMD [ "fastapi", "run", "./src/data_provider.py", "--workers=2", "--host=0.0.0.0", "--port=8000" ]
CMD [ "uvicorn", "data_provider:app", "--app-dir=src", "--workers=2", "--host=0.0.0.0", "--port=8000" ]