FROM python:3.12-slim-bookworm

WORKDIR /app

COPY ebpf-only/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY common /app/common
COPY ebpf-only/main.py /app/main.py

ENV PORT=8080
EXPOSE 8080

CMD ["python", "main.py"]
