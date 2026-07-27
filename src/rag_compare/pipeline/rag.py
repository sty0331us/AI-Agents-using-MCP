"""End-to-end RAG answer generation on top of a chosen retriever."""

from __future__ import annotations

import time

from rag_compare.llm import LLMClient
from rag_compare.models import RagAnswer
from rag_compare.retrievers.base import Retriever

_ANSWER_SYSTEM = """You are a production RAG assistant.
Answer ONLY using the provided context passages.
If the context is insufficient, say what is missing.
Cite supporting passage ranks like [1], [2].
Keep answers concise and operational."""


class RagPipeline:
    def __init__(self, retriever: Retriever, llm: LLMClient) -> None:
        self._retriever = retriever
        self._llm = llm

    def answer(self, query: str, *, top_k: int = 5) -> RagAnswer:
        started = time.perf_counter()
        retrieval = self._retriever.retrieve(query, top_k=top_k)
        context = self._format_context(retrieval.documents)
        gen_started = time.perf_counter()
        answer = self._llm.complete(
            _ANSWER_SYSTEM,
            f"Question: {query}\n\nContext:\n{context}\n\nAnswer:",
        )
        generation_latency_ms = (time.perf_counter() - gen_started) * 1000.0
        total_latency_ms = (time.perf_counter() - started) * 1000.0
        return RagAnswer(
            query=query,
            answer=answer.strip(),
            citations=retrieval.documents,
            retrieval=retrieval,
            generation_latency_ms=generation_latency_ms,
            total_latency_ms=total_latency_ms,
        )

    @staticmethod
    def _format_context(docs) -> str:
        if not docs:
            return "(no passages retrieved)"
        blocks = []
        for item in docs:
            source = item.document.metadata.get("source", "unknown")
            blocks.append(
                f"[{item.rank}] source={source} score={item.score:.4f}\n{item.document.content}"
            )
        return "\n\n".join(blocks)
