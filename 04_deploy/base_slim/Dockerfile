FROM python:3.12-slim
LABEL maintainer="alekszejenko.levente@vik.bme.hu"
RUN apt-get -y update && apt-get install --no-install-recommends -y wget && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir -U mlflow tensorflow-cpu fastapi uvicorn
ENV PYTHONUNBUFFERED=1
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV TF_ENABLE_ONEDNN_OPTS=0
ENV GIT_PYTHON_REFRESH=quiet
