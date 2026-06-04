FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" python-dotenv pydantic aiosqlite "redis[asyncio]"

COPY src/ ./src/

RUN mkdir -p /app/data

EXPOSE 8004

CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8004}"]
