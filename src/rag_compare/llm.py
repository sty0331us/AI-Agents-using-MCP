"""LLM abstractions used by multi-query and self-query retrievers."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from rag_compare.config import LLMBackend, Settings, get_settings
from rag_compare.logging_setup import get_logger

logger = get_logger(__name__)


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        raise NotImplementedError


class HeuristicLLM(LLMClient):
    """Offline stand-in that still exercises rewrite / filter code paths."""

    def complete(self, system: str, user: str) -> str:
        lowered = system.lower()
        if "rewrite" in lowered or "alternative queries" in lowered:
            return self._rewrite_queries(user)
        if "metadata filter" in lowered or "self-query" in lowered:
            return self._self_query_plan(user)
        if "answer" in lowered or "grounded" in lowered:
            return (
                "Based on the retrieved context, here is a concise answer. "
                "Prefer cited source passages when verifying claims."
            )
        return user

    def _rewrite_queries(self, query: str) -> str:
        base = query.strip().rstrip("?")
        variants = [
            base,
            f"explain {base}",
            f"{base} overview and key tradeoffs",
            f"what are the benefits of {base}",
        ]
        # Return JSON list for the multi-query parser
        return json.dumps(variants[:4])

    def _self_query_plan(self, query: str) -> str:
        filters: dict[str, Any] = {}
        # Lightweight keyword → metadata heuristics for the sample corpus
        topic_map = {
            "faiss": "vector_db",
            "chroma": "vector_db",
            "retriever": "retrieval",
            "multi-query": "retrieval",
            "parent document": "retrieval",
            "self-query": "retrieval",
            "embedding": "embeddings",
            "evaluation": "evaluation",
            "latency": "evaluation",
            "production": "ops",
            "observability": "ops",
        }
        q = query.lower()
        for needle, topic in topic_map.items():
            if needle in q:
                filters["topic"] = topic
                break
        for level in ("beginner", "intermediate", "advanced"):
            if level in q:
                filters["level"] = level
                break
        semantic = re.sub(
            r"\b(beginner|intermediate|advanced|topic|level|about|regarding)\b",
            " ",
            query,
            flags=re.IGNORECASE,
        )
        semantic = re.sub(r"\s+", " ", semantic).strip() or query
        return json.dumps({"query": semantic, "filter": filters})


class OpenAILLM(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("openai package is required for LLMBackend.OPENAI") from exc
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        return content or ""


def build_llm(settings: Settings | None = None) -> LLMClient:
    cfg = settings or get_settings()
    if cfg.llm_backend == LLMBackend.HEURISTIC:
        logger.info("llm_backend", extra={"backend": "heuristic"})
        return HeuristicLLM()
    if cfg.llm_backend == LLMBackend.OPENAI:
        if not cfg.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for openai llm")
        logger.info("llm_backend", extra={"backend": "openai", "model": cfg.openai_chat_model})
        return OpenAILLM(api_key=cfg.openai_api_key, model=cfg.openai_chat_model)
    raise ValueError(f"unsupported llm backend: {cfg.llm_backend}")
