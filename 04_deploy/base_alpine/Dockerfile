FROM python:3.14-alpine
LABEL maintainer="alekszejenko.levente@vik.bme.hu"
RUN apk add --no-cache wget py3-requests py3-fastapi uvicorn #py3-numpy
ENV PYTHONPATH=/usr/lib/python3.14/site-packages/
RUN pip3 install --no-cache-dir --target=/usr/lib/python3.14/site-packages/ -U numpy asyncer anyio #requests fastapi[standard]
ENV PYTHONUNBUFFERED=1
