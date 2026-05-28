"""
Qdrant vector store — upsert and query operations.
Chunk text and metadata are stored as Qdrant payloads (no GCS metadata needed).
RBAC filtering is done via Qdrant payload filters on the allowed_roles field.
"""

import os
import uuid
import hashlib
import logging

logger = logging.getLogger("rag-service.vector_store")

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "knowledge-base")
EMBEDDING_DIM   = 384   # all-MiniLM-L6-v2


def _get_client():
    """Return a Qdrant client."""
    from qdrant_client import QdrantClient
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    return QdrantClient(url=qdrant_url, timeout=30)


def _ensure_collection(client) -> None:
    """Create the collection if it does not exist."""
    from qdrant_client.models import Distance, VectorParams
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")


async def upsert_chunks(chunks: list[dict]) -> None:
    """
    Upsert embedded chunks to Qdrant.
    Each chunk must have an 'embedding' key plus text/source/metadata fields.
    Text and metadata are stored as Qdrant payload — no GCS chunk metadata needed.
    """
    from qdrant_client.models import PointStruct

    client = _get_client()
    _ensure_collection(client)

    points = []
    for chunk in chunks:
        allowed_roles = chunk.get("metadata", {}).get("allowed_roles", ["admin"])
        # Deterministic ID from source + chunk_index so re-ingestion overwrites, not duplicates
        stable_id = str(uuid.UUID(hashlib.md5(
            f"{chunk.get('source', '')}::{chunk.get('chunk_index', 0)}".encode()
        ).hexdigest()))
        points.append(
            PointStruct(
                id=stable_id,
                vector=chunk["embedding"],
                payload={
                    "text":          chunk.get("text", ""),
                    "source":        chunk.get("source", "unknown"),
                    "chunk_index":   chunk.get("chunk_index", -1),
                    "allowed_roles": allowed_roles,
                    **{k: v for k, v in chunk.get("metadata", {}).items()
                       if k != "allowed_roles"},
                },
            )
        )

    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        logger.info(f"Upserted batch {i // batch_size + 1}: {len(batch)} points")

    logger.info(f"Total upserted: {len(points)} chunks to '{COLLECTION_NAME}'")


async def query_index(
    embedding: list[float],
    top_k: int = 5,
    user_roles: list[str] = ["developer"],
) -> list[dict]:
    """
    Query Qdrant with role-based payload filtering.
    Returns list of {id, score, text, source, chunk_index, metadata}.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchAny

    client = _get_client()
    _ensure_collection(client)

    role_filter = Filter(
        must=[
            FieldCondition(
                key="allowed_roles",
                match=MatchAny(any=user_roles),
            )
        ]
    )

    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=embedding,
            query_filter=role_filter,
            limit=top_k,
            with_payload=True,
        ).points

        return [
            {
                "id":          str(r.id),
                "score":       round(r.score, 4),
                "text":        r.payload.get("text", ""),
                "source":      r.payload.get("source", "unknown"),
                "chunk_index": r.payload.get("chunk_index", -1),
                "metadata":    {k: v for k, v in r.payload.items()
                                if k not in ("text", "source", "chunk_index", "allowed_roles")},
            }
            for r in results
        ]

    except Exception as e:
        logger.error(f"Qdrant query failed: {e}")
        return []
