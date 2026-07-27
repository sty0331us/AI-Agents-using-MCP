"""FastAPI surface for production-style retrieve / compare / answer."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag_compare import __version__
from rag_compare.config import VectorBackend, get_settings
from rag_compare.logging_setup import configure_logging, get_logger
from rag_compare.models import RetrieverKind
from rag_compare.service import get_service

logger = get_logger(__name__)
settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="RAG Retriever Comparison API",
    description=(
        "Production-oriented API for comparing vector, multi-query, "
        "self-query, and parent-document retrievers on FAISS or Chroma."
    ),
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    vector_backend: VectorBackend = VectorBackend.FAISS


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    strategy: RetrieverKind = RetrieverKind.VECTOR
    top_k: int = Field(default=5, ge=1, le=50)


class CompareRequest(BaseModel):
    queries: list[str] = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    relevant_ids_by_query: dict[str, list[str]] | None = None


class AnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    strategy: RetrieverKind = RetrieverKind.VECTOR
    top_k: int = Field(default=5, ge=1, le=50)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = request.headers.get(settings.request_id_header) or uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers[settings.request_id_header] = request_id
    return response


@app.get("/health")
def health() -> dict[str, Any]:
    service = get_service()
    return {"status": "ok", "version": __version__, **service.status()}


@app.get("/status")
def status() -> dict[str, Any]:
    return get_service().status()


@app.post("/ingest")
def ingest(body: IngestRequest) -> dict[str, Any]:
    try:
        return get_service().ingest(body.vector_backend)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("ingest_failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/retrieve")
def retrieve(body: RetrieveRequest) -> dict[str, Any]:
    try:
        result = get_service().retrieve(body.query, strategy=body.strategy, top_k=body.top_k)
        return result.model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/compare")
def compare(body: CompareRequest) -> dict[str, Any]:
    try:
        report = get_service().compare(
            body.queries,
            top_k=body.top_k,
            relevant_ids_by_query=body.relevant_ids_by_query,
        )
        return report.model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/answer")
def answer(body: AnswerRequest) -> dict[str, Any]:
    try:
        result = get_service().answer(body.query, strategy=body.strategy, top_k=body.top_k)
        return result.model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
