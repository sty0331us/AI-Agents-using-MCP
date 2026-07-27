"""FAISS-backed vector store with on-disk persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from rag_compare.logging_setup import get_logger
from rag_compare.models import Document
from rag_compare.stores.base import VectorStore, matches_filter

logger = get_logger(__name__)


class FaissVectorStore(VectorStore):
    """Inner-product FAISS index over L2-normalized vectors (= cosine)."""

    def __init__(self, dimension: int, persist_dir: Path | None = None, index_name: str = "default") -> None:
        try:
            import faiss  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("faiss-cpu is required for FaissVectorStore") from exc

        self._dimension = dimension
        self._persist_dir = persist_dir
        self._index_name = index_name
        self._documents: dict[str, Document] = {}
        self._id_by_row: list[str] = []
        self._index = None
        if persist_dir is not None:
            persist_dir.mkdir(parents=True, exist_ok=True)
            self._try_load()
        if self._index is None:
            self._reset_index()

    def _reset_index(self) -> None:
        import faiss

        self._index = faiss.IndexFlatIP(self._dimension)
        self._documents.clear()
        self._id_by_row.clear()

    def upsert(self, documents: Sequence[Document], embeddings: Sequence[Sequence[float]]) -> int:
        if len(documents) != len(embeddings):
            raise ValueError("documents/embeddings length mismatch")
        if not documents:
            return 0

        import faiss

        vectors = np.asarray(embeddings, dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[1] != self._dimension:
            raise ValueError(
                f"expected embeddings shape (n, {self._dimension}), got {vectors.shape}"
            )
        # Re-normalize defensively
        faiss.normalize_L2(vectors)

        # Replace existing IDs by rebuilding when collisions occur (small-corp friendly).
        # For large production indexes, prefer IDMap2 + remove_ids.
        colliding = [doc.id for doc in documents if doc.id in self._documents]
        if colliding:
            survivors = [
                (doc_id, self._documents[doc_id])
                for doc_id in self._id_by_row
                if doc_id not in {c for c in colliding}
            ]
            if survivors:
                # Rebuild without colliding IDs, then add the new batch
                old_embeddings = self._export_embeddings(
                    [doc_id for doc_id, _ in survivors]
                )
                self._reset_index()
                survivor_docs = [doc for _, doc in survivors]
                self._append(survivor_docs, old_embeddings)
            else:
                self._reset_index()

        self._append(list(documents), vectors)
        self._persist()
        return len(documents)

    def _append(self, documents: list[Document], vectors: np.ndarray) -> None:
        assert self._index is not None
        self._index.add(vectors)
        for doc in documents:
            self._documents[doc.id] = doc
            self._id_by_row.append(doc.id)

    def _export_embeddings(self, ids: list[str]) -> np.ndarray:
        assert self._index is not None
        row_lookup = {doc_id: idx for idx, doc_id in enumerate(self._id_by_row)}
        rows = [row_lookup[doc_id] for doc_id in ids]
        vectors = np.vstack([self._index.reconstruct(row) for row in rows]).astype(np.float32)
        return vectors

    def similarity_search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        assert self._index is not None
        if self._index.ntotal == 0:
            return []

        import faiss

        query = np.asarray([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query)
        # Over-fetch when filtering so we still fill top_k after metadata cuts
        fetch = min(self._index.ntotal, max(top_k * 5, top_k))
        scores, indices = self._index.search(query, fetch)

        hits: list[tuple[Document, float]] = []
        for score, row in zip(scores[0].tolist(), indices[0].tolist()):
            if row < 0:
                continue
            doc_id = self._id_by_row[row]
            doc = self._documents[doc_id]
            if not matches_filter(doc.metadata, metadata_filter):
                continue
            hits.append((doc, float(score)))
            if len(hits) >= top_k:
                break
        return hits

    def get_by_ids(self, ids: Sequence[str]) -> list[Document]:
        return [self._documents[doc_id] for doc_id in ids if doc_id in self._documents]

    def count(self) -> int:
        assert self._index is not None
        return int(self._index.ntotal)

    def clear(self) -> None:
        self._reset_index()
        self._persist()

    def _meta_path(self) -> Path | None:
        if self._persist_dir is None:
            return None
        return self._persist_dir / f"{self._index_name}.meta.json"

    def _index_path(self) -> Path | None:
        if self._persist_dir is None:
            return None
        return self._persist_dir / f"{self._index_name}.faiss"

    def _persist(self) -> None:
        import faiss

        meta_path = self._meta_path()
        index_path = self._index_path()
        if meta_path is None or index_path is None or self._index is None:
            return
        payload = {
            "dimension": self._dimension,
            "id_by_row": self._id_by_row,
            "documents": {doc_id: doc.model_dump() for doc_id, doc in self._documents.items()},
        }
        meta_path.write_text(json.dumps(payload), encoding="utf-8")
        faiss.write_index(self._index, str(index_path))
        logger.debug("faiss_persisted", extra={"path": str(index_path), "count": self.count()})

    def _try_load(self) -> None:
        import faiss

        meta_path = self._meta_path()
        index_path = self._index_path()
        if meta_path is None or index_path is None:
            return
        if not meta_path.exists() or not index_path.exists():
            return
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        self._dimension = int(payload["dimension"])
        self._id_by_row = list(payload["id_by_row"])
        self._documents = {
            doc_id: Document.model_validate(raw)
            for doc_id, raw in payload["documents"].items()
        }
        self._index = faiss.read_index(str(index_path))
        logger.info("faiss_loaded", extra={"path": str(index_path), "count": self.count()})
