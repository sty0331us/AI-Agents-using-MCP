"""Vector store package exports and factory."""

from __future__ import annotations

from rag_compare.config import Settings, VectorBackend, get_settings
from rag_compare.stores.base import VectorStore
from rag_compare.stores.chroma_store import ChromaVectorStore
from rag_compare.stores.faiss_store import FaissVectorStore


def build_vector_store(
    backend: VectorBackend | str | None = None,
    *,
    dimension: int,
    settings: Settings | None = None,
    namespace: str | None = None,
) -> VectorStore:
    cfg = settings or get_settings()
    chosen = VectorBackend(backend or cfg.default_vector_backend)
    if chosen == VectorBackend.FAISS:
        persist = cfg.index_dir / "faiss"
        return FaissVectorStore(
            dimension=dimension,
            persist_dir=persist,
            index_name=namespace or cfg.faiss_index_name,
        )
    if chosen == VectorBackend.CHROMA:
        persist = cfg.index_dir / "chroma"
        return ChromaVectorStore(
            collection_name=namespace or cfg.chroma_collection,
            persist_dir=persist,
        )
    raise ValueError(f"unsupported vector backend: {chosen}")


__all__ = [
    "VectorStore",
    "FaissVectorStore",
    "ChromaVectorStore",
    "build_vector_store",
]
