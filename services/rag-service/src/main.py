"""
RAG Service — FastAPI app.
Endpoints:
  POST /ingest      — load docs from GCS, embed, upsert to Vertex AI Vector Search
  POST /retrieve    — embed query, search Vertex AI, return chunks (IAM-filtered)
  GET  /health
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.ingestion.pipeline import ingest_from_gcs
from src.retrieval.retriever import retrieve_chunks

app = FastAPI(title="RAG Service", version="0.1.0")


# ── Request / Response models ────────────────────────────────────────────────

class IngestRequest(BaseModel):
    prefix: str = ""                  # GCS prefix/folder to ingest
    allowed_roles: list[str] = []     # roles that can access these docs

class IngestResponse(BaseModel):
    ingested: int
    skipped: int
    prefix: str

class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5
    user_id: str = ""
    user_roles: list[str] = ["developer"]   # used for access control filtering

class RetrieveResponse(BaseModel):
    chunks: list[dict]
    query: str
    total: int


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "rag-service"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    try:
        result = await ingest_from_gcs(prefix=req.prefix, allowed_roles=req.allowed_roles)
        return IngestResponse(**result, prefix=req.prefix)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(req: RetrieveRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")
    try:
        chunks = await retrieve_chunks(
            query=req.query,
            top_k=req.top_k,
            user_id=req.user_id,
            user_roles=req.user_roles,
        )
        return RetrieveResponse(chunks=chunks, query=req.query, total=len(chunks))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
