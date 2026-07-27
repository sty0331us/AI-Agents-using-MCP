"""Multi-query retriever: expand the user query, retrieve, then fuse."""

from __future__ import annotations

import json
import time
from typing import Any

from rag_compare.embeddings import Embedder
from rag_compare.llm import LLMClient
from rag_compare.logging_setup import get_logger
from rag_compare.models import RetrieverKind, VectorBackendKind
from rag_compare.retrievers.base import Retriever, dedupe_by_id
from rag_compare.stores.base import VectorStore

logger = get_logger(__name__)

_REWRITE_SYSTEM = """You rewrite search queries for a retrieval system.
Return ONLY a JSON array of alternative queries (strings).
Include the original intent; do not add commentary."""


class MultiQueryRetriever(Retriever):
    """Improves recall by retrieving for several paraphrased queries and fusing hits."""

    kind = RetrieverKind.MULTI_QUERY

    def __init__(
        self,
        store: VectorStore,
        embedder: Embedder,
        llm: LLMClient,
        vector_backend: VectorBackendKind,
        *,
        query_count: int = 3,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._llm = llm
        self.vector_backend = vector_backend
        self._query_count = max(1, query_count)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ):
        started = time.perf_counter()
        variants = self._expand(query)
        per_query_k = max(top_k, top_k + 2)
        fused: list[tuple[Any, float]] = []
        for variant in variants:
            embedding = self._embedder.embed_query(variant)
            hits = self._store.similarity_search(
                embedding,
                top_k=per_query_k,
                metadata_filter=metadata_filter,
            )
            fused.extend(hits)

        ranked = dedupe_by_id(fused)
        return self._timed_result(
            query=query,
            hits=ranked,
            top_k=top_k,
            started=started,
            rewritten_queries=variants,
            metadata_filter=metadata_filter,
            notes=[f"expanded_to={len(variants)}", "fusion=max_score_dedupe"],
        )

    def _expand(self, query: str) -> list[str]:
        raw = self._llm.complete(_REWRITE_SYSTEM, query)
        variants = self._parse(raw)
        if query not in variants:
            variants.insert(0, query)
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for item in variants:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(item.strip())
        return unique[: self._query_count]

    @staticmethod
    def _parse(raw: str) -> list[str]:
        text = raw.strip()
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(item).strip() for item in data if str(item).strip()]
        except json.JSONDecodeError:
            logger.warning("multi_query_parse_fallback")
        # Fallback: split lines
        return [line.strip("- •\t ") for line in text.splitlines() if line.strip()]
