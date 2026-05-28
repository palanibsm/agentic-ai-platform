"""
Retriever — embeds the user query, searches Qdrant with RBAC filtering,
and returns ranked text chunks. Metadata is stored in Qdrant payloads.
"""

import logging
from src.embeddings.embedder import embed_text
from src.ingestion.vector_store import query_index

logger = logging.getLogger("rag-service.retrieval")


async def retrieve_chunks(
    query: str,
    top_k: int = 5,
    user_id: str = "",
    user_roles: list[str] = ["developer"],
) -> list[dict]:
    """
    Full RAG retrieval:
      1. Embed the query locally (sentence-transformers, no GCP dependency)
      2. Search Qdrant with role-based payload filter
      3. Return ranked chunks with source attribution
    """
    logger.info(f"Retrieving for user={user_id} roles={user_roles} query='{query[:80]}'")

    query_embedding = embed_text(query)

    chunks = await query_index(
        embedding=query_embedding,
        top_k=top_k,
        user_roles=user_roles,
    )

    if not chunks:
        logger.info("No results returned from Qdrant")
        return []

    logger.info(f"Returning {len(chunks)} chunks")
    return chunks
