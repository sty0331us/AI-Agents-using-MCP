"""Runtime configuration via environment variables and optional .env file."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingBackend(str, Enum):
    HASH = "hash"  # deterministic offline / CI
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence_transformers"


class LLMBackend(str, Enum):
    HEURISTIC = "heuristic"  # offline / CI without API keys
    OPENAI = "openai"


class VectorBackend(str, Enum):
    FAISS = "faiss"
    CHROMA = "chroma"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Paths
    corpus_dir: Path = Field(default=Path("data/corpus"))
    index_dir: Path = Field(default=Path("data/indexes"))
    eval_dir: Path = Field(default=Path("data/eval"))

    # Embedding / LLM
    embedding_backend: EmbeddingBackend = EmbeddingBackend.HASH
    llm_backend: LLMBackend = LLMBackend.HEURISTIC
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    sentence_transformer_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Vector store defaults
    default_vector_backend: VectorBackend = VectorBackend.FAISS
    chroma_collection: str = "rag_compare"
    faiss_index_name: str = "default"

    # Retrieval knobs
    top_k: int = Field(default=5, ge=1, le=50)
    child_chunk_size: int = Field(default=400, ge=50)
    child_chunk_overlap: int = Field(default=80, ge=0)
    parent_chunk_size: int = Field(default=1200, ge=100)
    multi_query_count: int = Field(default=3, ge=1, le=8)
    retrieval_timeout_s: float = Field(default=30.0, gt=0)

    # API / UI
    api_host: str = "127.0.0.1"
    api_port: int = 8090
    gradio_port: int = 7860
    log_level: str = "INFO"
    request_id_header: str = "X-Request-ID"

    @field_validator("corpus_dir", "index_dir", "eval_dir", mode="before")
    @classmethod
    def _coerce_path(cls, value: str | Path) -> Path:
        return Path(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
