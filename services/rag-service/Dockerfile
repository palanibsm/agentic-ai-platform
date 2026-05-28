FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir \
    fastapi uvicorn[standard] \
    sentence-transformers==3.0.1 \
    qdrant-client==1.9.1 \
    google-cloud-storage \
    httpx python-dotenv pydantic

# Pre-download embedding model into the image (avoids cold-start download)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY src/ ./src/

EXPOSE 8001

CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
