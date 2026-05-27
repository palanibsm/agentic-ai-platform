"""
Vertex AI Vector Search — upsert and query operations.
Chunk metadata is persisted to GCS so retrieval survives container restarts.
"""

import os
import json
import logging
import uuid

logger = logging.getLogger("rag-service.vector_store")

GCS_METADATA_PREFIX = "chunk-metadata"


def _gcs_client():
    from google.cloud import storage
    return storage.Client(project=os.environ["GCP_PROJECT_ID"])


def _save_metadata_to_gcs(chunks_with_ids: list[dict]) -> None:
    """Persist id→metadata mapping to GCS for durable retrieval."""
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        return
    try:
        client = _gcs_client()
        bucket = client.bucket(bucket_name)
        for item in chunks_with_ids:
            dp_id = item["dp_id"]
            meta = {
                "text":        item.get("text", ""),
                "source":      item.get("source", "unknown"),
                "chunk_index": item.get("chunk_index", -1),
                "metadata":    item.get("metadata", {}),
            }
            blob = bucket.blob(f"{GCS_METADATA_PREFIX}/{dp_id}.json")
            blob.upload_from_string(json.dumps(meta), content_type="application/json")
        logger.info(f"Saved {len(chunks_with_ids)} chunk metadata files to GCS")
    except Exception as e:
        logger.warning(f"Failed to save chunk metadata to GCS: {e}")


def fetch_metadata_from_gcs(dp_ids: list[str]) -> dict[str, dict]:
    """Fetch chunk metadata from GCS by datapoint IDs."""
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        return {}
    result = {}
    try:
        client = _gcs_client()
        bucket = client.bucket(bucket_name)
        for dp_id in dp_ids:
            try:
                blob = bucket.blob(f"{GCS_METADATA_PREFIX}/{dp_id}.json")
                data = json.loads(blob.download_as_text())
                result[dp_id] = data
            except Exception:
                result[dp_id] = {}
    except Exception as e:
        logger.warning(f"Failed to fetch chunk metadata from GCS: {e}")
    return result


def _get_index_endpoint():
    from google.cloud import aiplatform
    project     = os.environ["GCP_PROJECT_ID"]
    region      = os.getenv("GCP_REGION", "us-central1")
    endpoint_id = os.environ["VERTEX_AI_ENDPOINT_ID"]
    aiplatform.init(project=project, location=region)
    return aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_id)


async def upsert_chunks(chunks: list[dict]) -> None:
    """
    Upsert embedded chunks to Vertex AI Vector Search.
    Also persists id→metadata to GCS for durable retrieval.
    """
    project  = os.getenv("GCP_PROJECT_ID")
    index_id = os.getenv("VERTEX_AI_INDEX_ID")

    if not project or not index_id:
        logger.warning("Vertex AI not configured — skipping upsert")
        return

    try:
        from google.cloud import aiplatform
        region = os.getenv("GCP_REGION", "us-central1")
        aiplatform.init(project=project, location=region)
        index = aiplatform.MatchingEngineIndex(index_name=index_id)

        datapoints    = []
        chunks_with_ids = []

        for chunk in chunks:
            dp_id = str(uuid.uuid4())
            allowed_roles = chunk.get("metadata", {}).get("allowed_roles", ["admin"])

            datapoints.append({
                "datapoint_id":  dp_id,
                "feature_vector": chunk["embedding"],
                "restricts": [
                    {"namespace": "role",   "allow_list": allowed_roles},
                    {"namespace": "source", "allow_list": [chunk.get("source", "unknown")]},
                ],
                "crowding_tag": {"crowding_attribute": chunk.get("source", "")},
            })
            chunks_with_ids.append({**chunk, "dp_id": dp_id})

        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(datapoints), batch_size):
            batch = datapoints[i : i + batch_size]
            index.upsert_datapoints(datapoints=batch)
            logger.info(f"Upserted batch {i // batch_size + 1}: {len(batch)} datapoints")

        # Persist metadata to GCS
        _save_metadata_to_gcs(chunks_with_ids)

    except Exception as e:
        logger.error(f"Vertex AI upsert failed: {e}")
        raise


async def query_index(
    embedding: list[float],
    top_k: int = 5,
    user_roles: list[str] = ["developer"],
    deployed_index_id: str = "",
) -> list[dict]:
    """Query Vertex AI Vector Search. Returns list of {id, distance}."""
    project = os.getenv("GCP_PROJECT_ID")
    if not project:
        logger.warning("GCP_PROJECT_ID not set — returning empty results")
        return []

    deployed_index_id = deployed_index_id or os.getenv("VERTEX_AI_DEPLOYED_INDEX_ID", "deployed_index")

    try:
        endpoint = _get_index_endpoint()
        response = endpoint.find_neighbors(
            deployed_index_id=deployed_index_id,
            queries=[embedding],
            num_neighbors=top_k,
        )
        return [{"id": n.id, "distance": n.distance} for n in response[0]]

    except Exception as e:
        logger.error(f"Vertex AI query failed: {e}")
        return []
