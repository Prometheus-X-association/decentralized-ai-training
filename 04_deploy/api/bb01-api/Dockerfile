FROM python:3.12

RUN apt-get -y update
RUN apt-get install -y jq
RUN pip install fastapi[standard]
RUN pip install requests



COPY src/ .
COPY cfg/ .

EXPOSE 8000

RUN chmod +x bb01_api_runner.sh
RUN chmod +x login.sh

CMD ./bb01_api_runner.sh
