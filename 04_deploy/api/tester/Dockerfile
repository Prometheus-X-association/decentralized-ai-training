FROM python:3.12

RUN pip install fastapi[standard]
RUN pip install requests

COPY src/tester.py .

EXPOSE 8000

CMD fastapi run ./tester.py --workers 2 --host 0.0.0.0 --port 8000