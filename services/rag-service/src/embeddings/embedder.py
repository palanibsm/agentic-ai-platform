"""
Embeddings — uses sentence-transformers all-MiniLM-L6-v2 (local, no GCP dependency).
Model is baked into the Docker image at build time for fast cold starts.
"""

import logging
from functools import lru_cache

logger = logging.getLogger("rag-service.embeddings")

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM   = 384


@lru_cache(maxsize=1)
def _get_model():
    """Load and cache the embedding model (loaded once per process)."""
    from sentence_transformers import SentenceTransformer
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    logger.info("Embedding model loaded.")
    return model


def embed_text(text: str) -> list[float]:
    """Embed a single string. Returns a list of EMBEDDING_DIM floats."""
    model = _get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """Embed a list of texts in batches."""
    model = _get_model()
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        vectors = model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
        results.extend(vectors.tolist())
    return results
