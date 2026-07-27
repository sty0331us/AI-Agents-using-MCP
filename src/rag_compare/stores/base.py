"""Vector store protocol and shared helpers."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any, Sequence

from rag_compare.models import Document


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("vector length mismatch")
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    denom = math.sqrt(na) * math.sqrt(nb)
    if denom == 0:
        return 0.0
    return dot / denom


def matches_filter(metadata: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    for key, expected in filters.items():
        actual = metadata.get(key)
        if actual != expected:
            return False
    return True


class VectorStore(ABC):
    """Persistent or ephemeral similarity index over embedded documents."""

    @abstractmethod
    def upsert(self, documents: Sequence[Document], embeddings: Sequence[Sequence[float]]) -> int:
        raise NotImplementedError

    @abstractmethod
    def similarity_search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        """Return (document, score) pairs sorted by descending similarity."""

    @abstractmethod
    def get_by_ids(self, ids: Sequence[str]) -> list[Document]:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError
