FROM python:3.12-slim-bookworm

WORKDIR /app

COPY openlit-enabled/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY common /app/common
COPY openlit-enabled/main.py /app/main.py
COPY openlit-enabled/agent_sdk.py /app/agent_sdk.py

ENV PORT=8081
EXPOSE 8081

CMD ["python", "main.py"]
