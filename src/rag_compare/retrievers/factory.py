"""Factory that wires stores, embedders, and LLM into concrete retrievers."""

from __future__ import annotations

from dataclasses import dataclass

from rag_compare.config import Settings, VectorBackend, get_settings
from rag_compare.embeddings import Embedder, build_embedder
from rag_compare.llm import LLMClient, build_llm
from rag_compare.models import Document, RetrieverKind, VectorBackendKind
from rag_compare.retrievers.base import Retriever
from rag_compare.retrievers.multi_query import MultiQueryRetriever
from rag_compare.retrievers.parent_document import ParentDocumentRetriever
from rag_compare.retrievers.self_query import SelfQueryRetriever
from rag_compare.retrievers.vector import VectorStoreRetriever
from rag_compare.stores import VectorStore, build_vector_store


@dataclass
class RetrieverBundle:
    """All comparable strategies sharing one embedder / backend / corpus slice."""

    vector_backend: VectorBackendKind
    embedder: Embedder
    llm: LLMClient
    child_store: VectorStore
    parents: dict[str, Document]
    retrievers: dict[RetrieverKind, Retriever]


def build_retriever_bundle(
    *,
    vector_backend: VectorBackend | str | None = None,
    settings: Settings | None = None,
    namespace: str | None = None,
    parents: dict[str, Document] | None = None,
) -> RetrieverBundle:
    cfg = settings or get_settings()
    backend = VectorBackend(vector_backend or cfg.default_vector_backend)
    backend_kind = VectorBackendKind(backend.value)
    embedder = build_embedder(cfg)
    llm = build_llm(cfg)
    ns = namespace or f"{cfg.faiss_index_name}_{backend.value}"
    child_store = build_vector_store(
        backend,
        dimension=embedder.dimension,
        settings=cfg,
        namespace=f"{ns}_children",
    )
    parent_map = parents or {}

    vector = VectorStoreRetriever(child_store, embedder, backend_kind)
    multi = MultiQueryRetriever(
        child_store,
        embedder,
        llm,
        backend_kind,
        query_count=cfg.multi_query_count,
    )
    self_query = SelfQueryRetriever(child_store, embedder, llm, backend_kind)
    parent = ParentDocumentRetriever(child_store, embedder, parent_map, backend_kind)

    return RetrieverBundle(
        vector_backend=backend_kind,
        embedder=embedder,
        llm=llm,
        child_store=child_store,
        parents=parent_map,
        retrievers={
            RetrieverKind.VECTOR: vector,
            RetrieverKind.MULTI_QUERY: multi,
            RetrieverKind.SELF_QUERY: self_query,
            RetrieverKind.PARENT_DOCUMENT: parent,
        },
    )


def get_retriever(bundle: RetrieverBundle, kind: RetrieverKind | str) -> Retriever:
    key = RetrieverKind(kind)
    try:
        return bundle.retrievers[key]
    except KeyError as exc:
        raise ValueError(f"unknown retriever kind: {kind}") from exc
