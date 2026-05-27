"""
Ingestion pipeline — GCS → chunk → embed → Vertex AI Vector Search upsert.

Flow:
  1. List objects in GCS bucket under given prefix
  2. Download and parse each document (txt, md, pdf text layer)
  3. Chunk each document
  4. Embed chunks in batches
  5. Upsert to Vertex AI Vector Search index with metadata + access control
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger("rag-service.ingestion")

SUPPORTED_EXTENSIONS = {".txt", ".md", ".py", ".yaml", ".json"}


def _extract_text(content: bytes, filename: str) -> str:
    """Extract plain text from file bytes based on extension."""
    ext = Path(filename).suffix.lower()
    if ext in (".txt", ".md", ".py", ".yaml", ".json"):
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            return ""
    return ""


async def ingest_from_gcs(prefix: str = "", allowed_roles: list[str] = []) -> dict:
    """
    Ingest documents from GCS into Vertex AI Vector Search.
    Returns: {"ingested": int, "skipped": int}
    """
    from src.ingestion.chunker import chunk_text
    from src.embeddings.embedder import embed_batch
    from src.ingestion.vector_store import upsert_chunks

    bucket_name = os.getenv("GCS_BUCKET_NAME")
    project     = os.getenv("GCP_PROJECT_ID")
    region      = os.getenv("GCP_REGION", "us-central1")

    if not bucket_name or not project:
        logger.warning("GCS_BUCKET_NAME or GCP_PROJECT_ID not set — skipping real ingestion")
        return {"ingested": 0, "skipped": 0}

    from google.cloud import storage
    client = storage.Client(project=project)
    bucket = client.bucket(bucket_name)

    blobs = list(bucket.list_blobs(prefix=prefix))
    logger.info(f"Found {len(blobs)} objects under prefix '{prefix}'")

    all_chunks: list[dict] = []
    skipped = 0

    for blob in blobs:
        ext = Path(blob.name).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            skipped += 1
            continue
        try:
            content = blob.download_as_bytes()
            text = _extract_text(content, blob.name)
            if not text.strip():
                skipped += 1
                continue

            chunks = chunk_text(
                text=text,
                source=f"gs://{bucket_name}/{blob.name}",
                metadata={
                    "blob_name": blob.name,
                    "bucket": bucket_name,
                    "allowed_roles": allowed_roles or ["admin"],
                    "content_type": blob.content_type or "text/plain",
                    "size_bytes": blob.size,
                },
            )
            all_chunks.extend(chunks)
            logger.info(f"Chunked {blob.name} → {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"Failed to process {blob.name}: {e}")
            skipped += 1

    if not all_chunks:
        return {"ingested": 0, "skipped": skipped}

    # Batch embed
    texts = [c["text"] for c in all_chunks]
    logger.info(f"Embedding {len(texts)} chunks...")
    vectors = embed_batch(texts)

    # Attach vectors to chunks
    for chunk, vector in zip(all_chunks, vectors):
        chunk["embedding"] = vector

    # Upsert to Vertex AI Vector Search
    await upsert_chunks(all_chunks)

    logger.info(f"Ingestion complete: {len(all_chunks)} chunks upserted, {skipped} files skipped")
    return {"ingested": len(all_chunks), "skipped": skipped}
