FROM ghcr.io/alelevente/base_alpine:latest
WORKDIR /orchestrator
#COPY src/orchestrator.py .
#COPY src/model.py .
#COPY orchestrator_runner.sh .
COPY ./ ./
#RUN chmod +x orchestrator_runner.sh
EXPOSE 8000
ENV ROOT_PATH="/"
#CMD ./orchestrator_runner.sh
#CMD [ "fastapi", "run", "./src/orchestrator.py", "--host=0.0.0.0", "--port=8000", "--workers=4", \
CMD [ "uvicorn", "orchestrator:app", "--app-dir=src", "--host=0.0.0.0", "--port=8000", "--workers=4", \
                                        "--proxy-headers", "--forwarded-allow-ips='*'" ]
