"""Application service that owns ingest state and exposes compare/RAG operations."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any

from rag_compare.config import Settings, VectorBackend, get_settings
from rag_compare.logging_setup import get_logger
from rag_compare.models import (
    ComparisonReport,
    RagAnswer,
    RetrievalResult,
    RetrieverKind,
)
from rag_compare.pipeline.compare import compare_retrievers
from rag_compare.pipeline.ingest import (
    IngestResult,
    build_parent_child_documents,
    load_corpus,
)
from rag_compare.pipeline.rag import RagPipeline
from rag_compare.retrievers.factory import RetrieverBundle, build_retriever_bundle, get_retriever

logger = get_logger(__name__)


@dataclass
class ServiceState:
    bundle: RetrieverBundle | None = None
    ingest: IngestResult | None = None
    vector_backend: VectorBackend | None = None


class RagCompareService:
    """Process-local service suitable for API workers and Gradio.

    Thread-safe for read-mostly compare/retrieve after a single ingest.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._state = ServiceState()
        self._lock = RLock()

    @property
    def ready(self) -> bool:
        return self._state.bundle is not None and self._state.ingest is not None

    def status(self) -> dict[str, Any]:
        with self._lock:
            ingest = self._state.ingest
            return {
                "ready": self.ready,
                "vector_backend": (
                    self._state.vector_backend.value if self._state.vector_backend else None
                ),
                "parents": len(ingest.parents) if ingest else 0,
                "children": len(ingest.children) if ingest else 0,
                "upserted": ingest.upserted if ingest else 0,
                "embedding_backend": self.settings.embedding_backend.value,
                "llm_backend": self.settings.llm_backend.value,
            }

    def ingest(self, vector_backend: VectorBackend | str | None = None) -> dict[str, Any]:
        backend = VectorBackend(vector_backend or self.settings.default_vector_backend)
        with self._lock:
            source_docs = load_corpus(self.settings.corpus_dir)
            parents, children = build_parent_child_documents(
                source_docs,
                parent_chunk_size=self.settings.parent_chunk_size,
                child_chunk_size=self.settings.child_chunk_size,
                child_overlap=self.settings.child_chunk_overlap,
            )
            bundle = build_retriever_bundle(
                vector_backend=backend,
                settings=self.settings,
                namespace=f"prod_{backend.value}",
                parents=parents,
            )
            embeddings = bundle.embedder.embed_documents([c.content for c in children])
            bundle.child_store.clear()
            upserted = bundle.child_store.upsert(children, embeddings)
            result = IngestResult(parents=parents, children=children, upserted=upserted)
            self._state = ServiceState(bundle=bundle, ingest=result, vector_backend=backend)
            logger.info(
                "service_ingest_ready",
                extra={"backend": backend.value, "upserted": upserted},
            )
            return self.status()

    def _require_bundle(self) -> RetrieverBundle:
        if self._state.bundle is None:
            raise RuntimeError("Corpus not ingested. Call /ingest first.")
        return self._state.bundle

    def retrieve(
        self,
        query: str,
        *,
        strategy: RetrieverKind | str = RetrieverKind.VECTOR,
        top_k: int | None = None,
    ) -> RetrievalResult:
        with self._lock:
            bundle = self._require_bundle()
            retriever = get_retriever(bundle, strategy)
            return retriever.retrieve(query, top_k=top_k or self.settings.top_k)

    def compare(
        self,
        queries: list[str],
        *,
        top_k: int | None = None,
        relevant_ids_by_query: dict[str, list[str]] | None = None,
    ) -> ComparisonReport:
        with self._lock:
            bundle = self._require_bundle()
            labels = None
            if relevant_ids_by_query is not None:
                labels = {q: set(ids) for q, ids in relevant_ids_by_query.items()}
            report, _ = compare_retrievers(
                bundle,
                queries,
                top_k=top_k or self.settings.top_k,
                relevant_ids_by_query=labels,
            )
            return report

    def answer(
        self,
        query: str,
        *,
        strategy: RetrieverKind | str = RetrieverKind.VECTOR,
        top_k: int | None = None,
    ) -> RagAnswer:
        with self._lock:
            bundle = self._require_bundle()
            retriever = get_retriever(bundle, strategy)
            pipeline = RagPipeline(retriever, bundle.llm)
            return pipeline.answer(query, top_k=top_k or self.settings.top_k)


_service: RagCompareService | None = None


def get_service() -> RagCompareService:
    global _service
    if _service is None:
        _service = RagCompareService()
    return _service
