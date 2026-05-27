"""
Retriever — embeds the user query, searches Vertex AI Vector Search,
applies IAM access control filtering, and returns ranked text chunks.
"""

import os
import logging

from src.embeddings.embedder import embed_text
from src.ingestion.vector_store import query_index, fetch_metadata_from_gcs

logger = logging.getLogger("rag-service.retrieval")

# In-memory chunk store for tests/local dev (keyed by datapoint_id)
_CHUNK_STORE: dict[str, dict] = {}


def register_chunks(chunks: list[dict]) -> None:
    """Register chunks in the local store (used in tests and local dev)."""
    for chunk in chunks:
        _CHUNK_STORE[chunk.get("id", str(chunk.get("chunk_index", "")))] = chunk


async def retrieve_chunks(
    query: str,
    top_k: int = 5,
    user_id: str = "",
    user_roles: list[str] = ["developer"],
) -> list[dict]:
    """
    Full RAG retrieval:
      1. Embed the query
      2. Search Vertex AI Vector Search
      3. Fetch chunk metadata from GCS (durable) or in-memory store (tests)
      4. Return ranked chunks with source attribution
    """
    logger.info(f"Retrieving for user={user_id} roles={user_roles} query='{query[:80]}'")

    query_embedding = embed_text(query)

    neighbors = await query_index(
        embedding=query_embedding,
        top_k=top_k,
        user_roles=user_roles,
    )

    if not neighbors:
        logger.info("No neighbors returned from Vertex AI")
        return []

    dp_ids = [n["id"] for n in neighbors]

    # Try GCS first (production), fall back to in-memory (tests/local)
    gcs_meta = fetch_metadata_from_gcs(dp_ids) if os.getenv("GCS_BUCKET_NAME") else {}

    chunks_out: list[dict] = []
    for neighbor in neighbors:
        dp_id    = neighbor["id"]
        distance = neighbor.get("distance", 1.0)
        score    = round(1.0 - distance, 4)

        chunk = gcs_meta.get(dp_id) or _CHUNK_STORE.get(dp_id, {})
        chunks_out.append({
            "id":          dp_id,
            "text":        chunk.get("text", ""),
            "source":      chunk.get("source", "unknown"),
            "score":       score,
            "chunk_index": chunk.get("chunk_index", -1),
            "metadata":    chunk.get("metadata", {}),
        })

    chunks_out.sort(key=lambda x: x["score"], reverse=True)
    logger.info(f"Returning {len(chunks_out)} chunks")
    return chunks_out
