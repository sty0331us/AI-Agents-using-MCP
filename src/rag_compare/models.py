"""Domain models for documents, retrieval, and comparison reports."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "doc") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class RetrieverKind(str, Enum):
    VECTOR = "vector"
    MULTI_QUERY = "multi_query"
    SELF_QUERY = "self_query"
    PARENT_DOCUMENT = "parent_document"


class VectorBackendKind(str, Enum):
    FAISS = "faiss"
    CHROMA = "chroma"


class Document(BaseModel):
    """Canonical document unit used across ingest, index, and retrieve."""

    id: str = Field(default_factory=lambda: new_id("doc"))
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    parent_id: str | None = None

    @field_validator("content")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("document content must be non-empty")
        return cleaned


class ScoredDocument(BaseModel):
    document: Document
    score: float
    rank: int


class RetrievalTrace(BaseModel):
    """Opaque but structured debug trail for production incident review."""

    strategy: RetrieverKind
    vector_backend: VectorBackendKind
    rewritten_queries: list[str] = Field(default_factory=list)
    metadata_filter: dict[str, Any] | None = None
    notes: list[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    query: str
    documents: list[ScoredDocument]
    latency_ms: float
    trace: RetrievalTrace
    request_id: str = Field(default_factory=lambda: new_id("req"))
    retrieved_at: datetime = Field(default_factory=_utcnow)


class StrategyMetrics(BaseModel):
    strategy: RetrieverKind
    vector_backend: VectorBackendKind
    latency_ms_p50: float
    latency_ms_p95: float
    latency_ms_mean: float
    hit_rate_at_k: float
    mrr: float
    mean_docs_returned: float
    sample_count: int
    errors: int = 0


class ComparisonReport(BaseModel):
    query_count: int
    top_k: int
    generated_at: datetime = Field(default_factory=_utcnow)
    strategies: list[StrategyMetrics]
    winner_by_mrr: RetrieverKind | None = None
    winner_by_latency: RetrieverKind | None = None
    summary: str = ""


class RagAnswer(BaseModel):
    query: str
    answer: str
    citations: list[ScoredDocument]
    retrieval: RetrievalResult
    generation_latency_ms: float
    total_latency_ms: float
