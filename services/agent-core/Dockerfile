FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir \
    fastapi uvicorn[standard] langgraph langchain langchain-anthropic langchain-openai \
    httpx google-cloud-pubsub python-dotenv pydantic

COPY src/ ./src/
# Copy skills directory so the registry can load SKILL.md files at runtime
COPY skills/ ./skills/

EXPOSE 8002

CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8002}"]
