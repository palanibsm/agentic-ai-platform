FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir "litellm[proxy]" prisma

COPY config.yaml ./config.yaml
COPY guardrails/ ./guardrails/
COPY callbacks/ ./callbacks/

EXPOSE 4000

CMD ["sh", "-c", "litellm --config config.yaml --port ${PORT:-4000} --host 0.0.0.0"]
