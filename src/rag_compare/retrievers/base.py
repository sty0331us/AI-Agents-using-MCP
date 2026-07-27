"""Retriever protocol and shared ranking helpers."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from rag_compare.models import (
    Document,
    RetrievalResult,
    RetrievalTrace,
    RetrieverKind,
    ScoredDocument,
    VectorBackendKind,
)


def dedupe_by_id(
    hits: list[tuple[Document, float]],
) -> list[tuple[Document, float]]:
    best: dict[str, tuple[Document, float]] = {}
    for doc, score in hits:
        current = best.get(doc.id)
        if current is None or score > current[1]:
            best[doc.id] = (doc, score)
    return sorted(best.values(), key=lambda item: item[1], reverse=True)


def to_scored(hits: list[tuple[Document, float]], top_k: int) -> list[ScoredDocument]:
    ranked = hits[:top_k]
    return [
        ScoredDocument(document=doc, score=score, rank=idx + 1)
        for idx, (doc, score) in enumerate(ranked)
    ]


class Retriever(ABC):
    kind: RetrieverKind
    vector_backend: VectorBackendKind

    @abstractmethod
    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> RetrievalResult:
        raise NotImplementedError

    def _timed_result(
        self,
        *,
        query: str,
        hits: list[tuple[Document, float]],
        top_k: int,
        started: float,
        rewritten_queries: list[str] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        notes: list[str] | None = None,
    ) -> RetrievalResult:
        latency_ms = (time.perf_counter() - started) * 1000.0
        return RetrievalResult(
            query=query,
            documents=to_scored(hits, top_k),
            latency_ms=latency_ms,
            trace=RetrievalTrace(
                strategy=self.kind,
                vector_backend=self.vector_backend,
                rewritten_queries=rewritten_queries or [],
                metadata_filter=metadata_filter,
                notes=notes or [],
            ),
        )
