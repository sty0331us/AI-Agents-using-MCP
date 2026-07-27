"""ChromaDB-backed vector store."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from rag_compare.logging_setup import get_logger
from rag_compare.models import Document
from rag_compare.stores.base import VectorStore

logger = get_logger(__name__)


class ChromaVectorStore(VectorStore):
    def __init__(
        self,
        collection_name: str = "rag_compare",
        persist_dir: Path | None = None,
    ) -> None:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("chromadb is required for ChromaVectorStore") from exc

        if persist_dir is not None:
            persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        else:
            self._client = chromadb.Client(
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._collection_name = collection_name

    def upsert(self, documents: Sequence[Document], embeddings: Sequence[Sequence[float]]) -> int:
        if len(documents) != len(embeddings):
            raise ValueError("documents/embeddings length mismatch")
        if not documents:
            return 0
        self._collection.upsert(
            ids=[doc.id for doc in documents],
            documents=[doc.content for doc in documents],
            metadatas=[self._sanitize_metadata(doc) for doc in documents],
            embeddings=[list(map(float, emb)) for emb in embeddings],
        )
        logger.debug(
            "chroma_upserted",
            extra={"collection": self._collection_name, "count": len(documents)},
        )
        return len(documents)

    def similarity_search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        if self.count() == 0:
            return []
        kwargs: dict[str, Any] = {
            "query_embeddings": [list(map(float, query_embedding))],
            "n_results": min(top_k, self.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if metadata_filter:
            kwargs["where"] = metadata_filter
        result = self._collection.query(**kwargs)
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        hits: list[tuple[Document, float]] = []
        for doc_id, content, metadata, distance in zip(ids, documents, metadatas, distances):
            meta = dict(metadata or {})
            parent_id = meta.pop("parent_id", None)
            # Chroma cosine distance → similarity
            score = 1.0 - float(distance)
            hits.append(
                (
                    Document(
                        id=doc_id,
                        content=content or "",
                        metadata=meta,
                        parent_id=parent_id,
                    ),
                    score,
                )
            )
        return hits

    def get_by_ids(self, ids: Sequence[str]) -> list[Document]:
        if not ids:
            return []
        result = self._collection.get(ids=list(ids), include=["documents", "metadatas"])
        out: list[Document] = []
        for doc_id, content, metadata in zip(
            result.get("ids") or [],
            result.get("documents") or [],
            result.get("metadatas") or [],
        ):
            meta = dict(metadata or {})
            parent_id = meta.pop("parent_id", None)
            out.append(
                Document(id=doc_id, content=content or "", metadata=meta, parent_id=parent_id)
            )
        return out

    def count(self) -> int:
        return int(self._collection.count())

    def clear(self) -> None:
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _sanitize_metadata(doc: Document) -> dict[str, Any]:
        # Chroma only accepts str/int/float/bool metadata values
        meta: dict[str, Any] = {}
        for key, value in doc.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                meta[key] = value
            else:
                meta[key] = str(value)
        if doc.parent_id:
            meta["parent_id"] = doc.parent_id
        return meta
