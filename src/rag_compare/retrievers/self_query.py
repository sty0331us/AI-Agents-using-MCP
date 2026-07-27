"""Self-querying retriever: LLM extracts semantic query + metadata filters."""

from __future__ import annotations

import json
import time
from typing import Any

from rag_compare.embeddings import Embedder
from rag_compare.llm import LLMClient
from rag_compare.logging_setup import get_logger
from rag_compare.models import RetrieverKind, VectorBackendKind
from rag_compare.retrievers.base import Retriever
from rag_compare.stores.base import VectorStore

logger = get_logger(__name__)

_SELF_QUERY_SYSTEM = """You convert a natural-language question into a self-query plan.
Return ONLY JSON with keys:
  "query": string (semantic search text without filter phrases)
  "filter": object of metadata equality filters (may be empty)
Allowed filter keys: topic, level, source.
Example: {"query":"faiss vs chroma","filter":{"topic":"vector_db","level":"advanced"}}
"""


class SelfQueryRetriever(Retriever):
    """Useful when the corpus carries structured metadata the user implies in language."""

    kind = RetrieverKind.SELF_QUERY

    def __init__(
        self,
        store: VectorStore,
        embedder: Embedder,
        llm: LLMClient,
        vector_backend: VectorBackendKind,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._llm = llm
        self.vector_backend = vector_backend

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ):
        started = time.perf_counter()
        semantic_query, planned_filter = self._plan(query)
        merged_filter = {**(planned_filter or {}), **(metadata_filter or {})} or None

        embedding = self._embedder.embed_query(semantic_query)
        hits = self._store.similarity_search(
            embedding,
            top_k=top_k,
            metadata_filter=merged_filter,
        )

        # Soft fallback: if filters were too strict, retry without them
        notes = ["self_query_plan_applied"]
        if not hits and merged_filter:
            notes.append("filter_fallback_unconstrained")
            hits = self._store.similarity_search(
                embedding,
                top_k=top_k,
                metadata_filter=None,
            )

        return self._timed_result(
            query=query,
            hits=hits,
            top_k=top_k,
            started=started,
            rewritten_queries=[semantic_query],
            metadata_filter=merged_filter,
            notes=notes,
        )

    def _plan(self, query: str) -> tuple[str, dict[str, Any]]:
        raw = self._llm.complete(_SELF_QUERY_SYSTEM, query)
        try:
            data = json.loads(raw)
            semantic = str(data.get("query") or query).strip()
            filt = data.get("filter") or {}
            if not isinstance(filt, dict):
                filt = {}
            clean = {
                str(k): v
                for k, v in filt.items()
                if isinstance(v, (str, int, float, bool))
            }
            return semantic or query, clean
        except json.JSONDecodeError:
            logger.warning("self_query_parse_fallback")
            return query, {}
