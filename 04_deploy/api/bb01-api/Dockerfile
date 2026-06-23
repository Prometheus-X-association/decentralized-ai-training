FROM python:3.12

RUN pip install fastapi[standard]
RUN pip install requests

COPY 03_dev/api/bb01_api.py .
COPY 03_dev/api/bb01_registry.json .
COPY 03_dev/api/credentials.json .

EXPOSE 8000

CMD fastapi run ./bb01_api.py --workers 2 --host 0.0.0.0 --port 8000
