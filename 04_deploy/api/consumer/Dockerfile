FROM python:3.12

RUN pip install fastapi[standard]
RUN pip install requests

COPY 03_dev/api/consumer.py .

EXPOSE 8000

CMD fastapi run ./consumer.py --workers 2 --host 0.0.0.0 --port 8000