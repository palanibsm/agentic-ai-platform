"""
Embeddings — wraps Vertex AI text-embedding-004 model.
Falls back to a simple hash-based stub when GCP creds are unavailable (unit tests).
"""

import os
import hashlib
import logging
from functools import lru_cache

logger = logging.getLogger("rag-service.embeddings")

EMBEDDING_MODEL = "text-embedding-004"   # Vertex AI model
EMBEDDING_DIM   = 768                    # dimension for text-embedding-004


def _stub_embed(text: str) -> list[float]:
    """Deterministic stub embedding for tests — not for production."""
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
    import random
    rng = random.Random(seed)
    vec = [rng.gauss(0, 1) for _ in range(EMBEDDING_DIM)]
    # L2-normalise
    norm = sum(x ** 2 for x in vec) ** 0.5
    return [x / norm for x in vec]


@lru_cache(maxsize=1)
def _get_vertex_model(project: str, region: str):
    """Load and cache the Vertex AI embedding model (loaded once per process)."""
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel

    aiplatform.init(project=project, location=region)
    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
    logger.info(f"Loaded Vertex AI embedding model: {EMBEDDING_MODEL}")
    return model


def embed_text(text: str) -> list[float]:
    """
    Embed a single string using Vertex AI text-embedding-004.
    Returns a list of EMBEDDING_DIM floats.
    """
    project = os.getenv("GCP_PROJECT_ID")
    region  = os.getenv("GCP_REGION", "us-central1")

    if not project:
        logger.warning("GCP_PROJECT_ID not set — using stub embeddings")
        return _stub_embed(text)

    try:
        model = _get_vertex_model(project, region)
        embeddings = model.get_embeddings([text])
        return embeddings[0].values

    except Exception as e:
        logger.error(f"Vertex AI embedding failed, falling back to stub: {e}")
        return _stub_embed(text)


def embed_batch(texts: list[str], batch_size: int = 20) -> list[list[float]]:
    """Embed a list of texts in batches (Vertex AI limit: 250 per call)."""
    project = os.getenv("GCP_PROJECT_ID")
    region  = os.getenv("GCP_REGION", "us-central1")

    if not project:
        return [_stub_embed(t) for t in texts]

    results: list[list[float]] = []
    try:
        model = _get_vertex_model(project, region)

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = model.get_embeddings(batch)
            results.extend([e.values for e in embeddings])

    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        results = [_stub_embed(t) for t in texts]

    return results
