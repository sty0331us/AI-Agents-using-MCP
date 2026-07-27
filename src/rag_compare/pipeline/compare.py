"""Side-by-side retriever comparison orchestration."""

from __future__ import annotations

from typing import Iterable

from rag_compare.evaluation.metrics import evaluate_strategy_runs
from rag_compare.logging_setup import get_logger
from rag_compare.models import (
    ComparisonReport,
    RetrievalResult,
    RetrieverKind,
)
from rag_compare.retrievers.factory import RetrieverBundle, get_retriever

logger = get_logger(__name__)


def compare_retrievers(
    bundle: RetrieverBundle,
    queries: Iterable[str],
    *,
    top_k: int = 5,
    relevant_ids_by_query: dict[str, set[str]] | None = None,
    strategies: Iterable[RetrieverKind] | None = None,
) -> tuple[ComparisonReport, dict[str, list[RetrievalResult]]]:
    """Run every strategy on the same query set and summarize metrics.

    ``relevant_ids_by_query`` maps query text → set of relevant document IDs
    (parent or child). When omitted, ranking metrics that need labels are 0
    and the report still returns latency / volume diagnostics.
    """
    query_list = [q.strip() for q in queries if q and q.strip()]
    if not query_list:
        raise ValueError("queries must be non-empty")

    kinds = list(strategies) if strategies else list(RetrieverKind)
    per_strategy_results: dict[str, list[RetrievalResult]] = {}
    metrics = []

    for kind in kinds:
        retriever = get_retriever(bundle, kind)
        runs: list[RetrievalResult] = []
        labels: list[set[str]] = []
        errors = 0
        for query in query_list:
            try:
                result = retriever.retrieve(query, top_k=top_k)
                runs.append(result)
            except Exception as exc:  # noqa: BLE001 - capture for report
                errors += 1
                logger.exception(
                    "retrieve_failed",
                    extra={"strategy": kind.value, "error": str(exc)},
                )
                continue
            if relevant_ids_by_query is not None:
                labels.append(relevant_ids_by_query.get(query, set()))
            else:
                labels.append(set())
        per_strategy_results[kind.value] = runs
        metrics.append(
            evaluate_strategy_runs(
                strategy=kind,
                vector_backend=bundle.vector_backend,
                results=runs,
                relevant_ids=labels,
                errors=errors,
            )
        )

    winner_mrr = max(metrics, key=lambda m: (m.mrr, -m.latency_ms_mean)).strategy if metrics else None
    winner_latency = (
        min(metrics, key=lambda m: (m.latency_ms_mean, -m.mrr)).strategy if metrics else None
    )
    summary = _summarize(metrics, winner_mrr, winner_latency)
    report = ComparisonReport(
        query_count=len(query_list),
        top_k=top_k,
        strategies=metrics,
        winner_by_mrr=winner_mrr,
        winner_by_latency=winner_latency,
        summary=summary,
    )
    return report, per_strategy_results


def _summarize(metrics, winner_mrr, winner_latency) -> str:
    if not metrics:
        return "No strategies evaluated."
    lines = [
        f"Evaluated {len(metrics)} retriever strategies.",
        f"Best MRR: {winner_mrr.value if winner_mrr else 'n/a'}.",
        f"Lowest mean latency: {winner_latency.value if winner_latency else 'n/a'}.",
    ]
    for item in sorted(metrics, key=lambda m: m.mrr, reverse=True):
        lines.append(
            f"- {item.strategy.value}/{item.vector_backend.value}: "
            f"MRR={item.mrr:.3f} hit@k={item.hit_rate_at_k:.3f} "
            f"p50={item.latency_ms_p50:.1f}ms p95={item.latency_ms_p95:.1f}ms"
        )
    return "\n".join(lines)
