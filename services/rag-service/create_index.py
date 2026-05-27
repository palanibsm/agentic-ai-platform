"""
Run this once to create a Vertex AI Vector Search index with STREAM_UPDATE enabled.
Usage: python create_index.py
"""

import os
from google.cloud import aiplatform

PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
if not PROJECT_ID:
    raise ValueError("GCP_PROJECT_ID env var not set")

print(f"Creating index in project={PROJECT_ID} region=us-central1")
print("This takes 30-60 minutes...")

aiplatform.init(project=PROJECT_ID, location="us-central1")

index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
    display_name="agentic-ai-index",
    dimensions=768,
    approximate_neighbors_count=10,
    distance_measure_type="DOT_PRODUCT_DISTANCE",
    index_update_method="STREAM_UPDATE",
    leaf_node_embedding_count=500,
    leaf_nodes_to_search_percent=7,
)

print(f"\nIndex created successfully!")
print(f"VERTEX_AI_INDEX_ID={index.name}")
print(f"Full resource name: {index.resource_name}")
print(f"\nNext: deploy this index to your endpoint:")
print(f"  gcloud ai index-endpoints deploy-index 6698429345574158336 \\")
print(f"    --deployed-index-id=deployed_index \\")
print(f"    --display-name=agentic-ai-deployed \\")
print(f"    --index={index.name} \\")
print(f"    --region=us-central1")
