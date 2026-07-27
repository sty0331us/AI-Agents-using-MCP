"""Classic vector-store-backed similarity retriever."""

from __future__ import annotations

import time
from typing import Any

from rag_compare.embeddings import Embedder
from rag_compare.models import RetrieverKind, VectorBackendKind
from rag_compare.retrievers.base import Retriever
from rag_compare.stores.base import VectorStore


class VectorStoreRetriever(Retriever):
    """Dense nearest-neighbor retrieval against a vector index."""

    kind = RetrieverKind.VECTOR

    def __init__(
        self,
        store: VectorStore,
        embedder: Embedder,
        vector_backend: VectorBackendKind,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self.vector_backend = vector_backend

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ):
        started = time.perf_counter()
        embedding = self._embedder.embed_query(query)
        hits = self._store.similarity_search(
            embedding,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )
        return self._timed_result(
            query=query,
            hits=hits,
            top_k=top_k,
            started=started,
            metadata_filter=metadata_filter,
            notes=["dense_similarity_search"],
        )
