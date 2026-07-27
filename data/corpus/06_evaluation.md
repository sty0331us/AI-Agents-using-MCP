---
title: Evaluating Retrievers in Production
topic: evaluation
level: intermediate
module: course-module-2
---

# Retriever Evaluation Metrics

Offline gates should land before online A/B tests.

## Core metrics

- **Hit rate@k**: fraction of queries where at least one relevant doc appears in the top-k.
- **MRR**: mean reciprocal rank of the first relevant hit.
- **Latency p50/p95**: user-visible retrieval time, excluding generation when comparing retrievers alone.
- **Mean docs returned**: detects silent filter failures.

## Operating cadence

1. Build a labeled eval set of real queries (even 30–50 is useful).
2. Compare strategies on the same corpus snapshot.
3. Promote winners behind a feature flag with shadow traffic.
4. Watch p95 latency and empty-result rate in production dashboards.
