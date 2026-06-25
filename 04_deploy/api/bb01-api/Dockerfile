FROM python:3.12

RUN pip install fastapi[standard]
RUN pip install requests

COPY src/bb01_api.py .
COPY cfg/ .

EXPOSE 8000

CMD fastapi run ./bb01_api.py --workers 2 --host 0.0.0.0 --port 8000
