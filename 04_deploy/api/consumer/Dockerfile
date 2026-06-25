FROM python:3.12

RUN pip install fastapi[standard]
RUN pip install requests

COPY src/consumer.py .

EXPOSE 8000

CMD fastapi run ./consumer.py --workers 2 --host 0.0.0.0 --port 8000