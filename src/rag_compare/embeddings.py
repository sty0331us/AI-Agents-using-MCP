"""Embedding provider abstractions and concrete backends."""

from __future__ import annotations

import hashlib
import math
import struct
from abc import ABC, abstractmethod
from typing import Sequence

from rag_compare.config import EmbeddingBackend, Settings, get_settings
from rag_compare.logging_setup import get_logger

logger = get_logger(__name__)


class Embedder(ABC):
    """Produces dense vectors for indexing and query-time search."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class HashEmbedder(Embedder):
    """Deterministic bag-of-features embedder for offline CI and demos.

    Not a semantic model — it keeps unit tests and local dry-runs free of
    network/API dependencies while preserving ranking stability.
    """

    def __init__(self, dimension: int = 384) -> None:
        if dimension < 8:
            raise ValueError("dimension must be >= 8")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self._dimension
        tokens = text.lower().split()
        if not tokens:
            tokens = ["_empty_"]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            # Mix several 4-byte windows into the vector
            for i in range(0, min(len(digest), 32), 4):
                idx = struct.unpack_from(">I", digest, i)[0] % self._dimension
                sign = 1.0 if digest[i] % 2 == 0 else -1.0
                vec[idx] += sign
        # L2 normalize for cosine-compatible FAISS/Chroma usage
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class OpenAIEmbedder(Embedder):
    def __init__(self, api_key: str, model: str, dimension: int = 1536) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "openai package is required for EmbeddingBackend.OPENAI"
            ) from exc
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        # OpenAI accepts batches; keep payload sizes practical
        batch_size = 64
        out: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = list(texts[start : start + batch_size])
            response = self._client.embeddings.create(model=self._model, input=batch)
            ordered = sorted(response.data, key=lambda item: item.index)
            out.extend([item.embedding for item in ordered])
        if out:
            self._dimension = len(out[0])
        return out


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "sentence-transformers is required for EmbeddingBackend.SENTENCE_TRANSFORMERS"
            ) from exc
        self._model = SentenceTransformer(model_name)
        self._dimension = int(self._model.get_sentence_embedding_dimension())

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]


def build_embedder(settings: Settings | None = None) -> Embedder:
    cfg = settings or get_settings()
    if cfg.embedding_backend == EmbeddingBackend.HASH:
        logger.info("embedder_backend", extra={"backend": "hash", "dim": cfg.embedding_dim})
        return HashEmbedder(dimension=cfg.embedding_dim)
    if cfg.embedding_backend == EmbeddingBackend.OPENAI:
        if not cfg.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for openai embeddings")
        logger.info(
            "embedder_backend",
            extra={"backend": "openai", "model": cfg.openai_embedding_model},
        )
        return OpenAIEmbedder(
            api_key=cfg.openai_api_key,
            model=cfg.openai_embedding_model,
            dimension=cfg.embedding_dim,
        )
    if cfg.embedding_backend == EmbeddingBackend.SENTENCE_TRANSFORMERS:
        logger.info(
            "embedder_backend",
            extra={"backend": "sentence_transformers", "model": cfg.sentence_transformer_model},
        )
        return SentenceTransformerEmbedder(cfg.sentence_transformer_model)
    raise ValueError(f"unsupported embedding backend: {cfg.embedding_backend}")
