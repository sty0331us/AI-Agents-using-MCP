"""Retrieval quality and latency metrics."""

from __future__ import annotations

import math
from statistics import mean, median
from typing import Sequence

from rag_compare.models import (
    Document,
    RetrievalResult,
    RetrieverKind,
    StrategyMetrics,
    VectorBackendKind,
)


def percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    if pct <= 0:
        return float(min(values))
    if pct >= 100:
        return float(max(values))
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[low])
    weight = rank - low
    return float(ordered[low] * (1 - weight) + ordered[high] * weight)


def relevance_keys(doc: Document) -> set[str]:
    """IDs and source names that can match an eval label."""
    keys = {doc.id}
    if doc.parent_id:
        keys.add(str(doc.parent_id))
    parent_meta = doc.metadata.get("parent_id")
    if parent_meta:
        keys.add(str(parent_meta))
    source = doc.metadata.get("source")
    if source:
        keys.add(str(source))
    return keys


def hit_rate_at_k(results: Sequence[RetrievalResult], relevant_ids: Sequence[set[str]]) -> float:
    if not results:
        return 0.0
    hits = 0
    labeled = 0
    for result, relevant in zip(results, relevant_ids):
        if not relevant:
            continue
        labeled += 1
        retrieved: set[str] = set()
        for scored in result.documents:
            retrieved |= relevance_keys(scored.document)
        if retrieved.intersection(relevant):
            hits += 1
    if labeled == 0:
        return 0.0
    return hits / labeled


def mean_reciprocal_rank(
    results: Sequence[RetrievalResult],
    relevant_ids: Sequence[set[str]],
) -> float:
    scores: list[float] = []
    for result, relevant in zip(results, relevant_ids):
        if not relevant:
            continue
        rr = 0.0
        for scored in result.documents:
            if relevance_keys(scored.document).intersection(relevant):
                rr = 1.0 / scored.rank
                break
        scores.append(rr)
    return mean(scores) if scores else 0.0


def evaluate_strategy_runs(
    *,
    strategy: RetrieverKind,
    vector_backend: VectorBackendKind,
    results: Sequence[RetrievalResult],
    relevant_ids: Sequence[set[str]],
    errors: int = 0,
) -> StrategyMetrics:
    latencies = [r.latency_ms for r in results]
    docs_counts = [len(r.documents) for r in results]
    return StrategyMetrics(
        strategy=strategy,
        vector_backend=vector_backend,
        latency_ms_p50=percentile(latencies, 50) if latencies else 0.0,
        latency_ms_p95=percentile(latencies, 95) if latencies else 0.0,
        latency_ms_mean=mean(latencies) if latencies else 0.0,
        hit_rate_at_k=hit_rate_at_k(results, relevant_ids),
        mrr=mean_reciprocal_rank(results, relevant_ids),
        mean_docs_returned=mean(docs_counts) if docs_counts else 0.0,
        sample_count=len(results),
        errors=errors,
    )


def latency_median(results: Sequence[RetrievalResult]) -> float:
    values = [r.latency_ms for r in results]
    return float(median(values)) if values else 0.0
