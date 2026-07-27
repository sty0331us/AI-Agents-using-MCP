"""Parent-document retriever: search small chunks, return parent context."""

from __future__ import annotations

import time
from typing import Any

from rag_compare.embeddings import Embedder
from rag_compare.models import Document, RetrieverKind, VectorBackendKind
from rag_compare.retrievers.base import Retriever, dedupe_by_id
from rag_compare.stores.base import VectorStore


class ParentDocumentRetriever(Retriever):
    """Indexes child chunks for precision, returns parent docs for generation context.

    Production pattern: embed fine-grained units for recall/precision, but feed the
    LLM the broader parent passage so answers keep surrounding context.
    """

    kind = RetrieverKind.PARENT_DOCUMENT

    def __init__(
        self,
        child_store: VectorStore,
        embedder: Embedder,
        parents: dict[str, Document],
        vector_backend: VectorBackendKind,
    ) -> None:
        self._child_store = child_store
        self._embedder = embedder
        self._parents = parents
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
        # Fetch extra children so parent dedupe still fills top_k
        child_hits = self._child_store.similarity_search(
            embedding,
            top_k=max(top_k * 3, top_k),
            metadata_filter=metadata_filter,
        )

        parent_hits: list[tuple[Document, float]] = []
        for child, score in child_hits:
            parent_id = child.parent_id or child.metadata.get("parent_id")
            if not parent_id:
                parent_hits.append((child, score))
                continue
            parent = self._parents.get(str(parent_id))
            if parent is None:
                parent_hits.append((child, score))
                continue
            parent_hits.append((parent, score))

        ranked = dedupe_by_id(parent_hits)
        return self._timed_result(
            query=query,
            hits=ranked,
            top_k=top_k,
            started=started,
            metadata_filter=metadata_filter,
            notes=[
                "search_unit=child_chunk",
                "return_unit=parent_document",
                f"parents_indexed={len(self._parents)}",
            ],
        )
