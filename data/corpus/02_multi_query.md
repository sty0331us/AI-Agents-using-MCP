---
title: Multi-Query Retrievers
topic: retrieval
level: advanced
module: course-module-1
---

# Multi-Query Retrievers

Multi-query retrieval asks an LLM to rewrite one user question into several paraphrases, retrieves for each rewrite, then fuses and deduplicates hits (commonly by max score per document id).

## Why recall improves

A single embedding query is a point estimate of intent. Paraphrases explore nearby regions of embedding space and recover documents that lexical mismatch would miss.

## Production tradeoffs

- Cost scales with rewrite count × retriever calls.
- Cap rewrite count (3 is a practical default) and cache paraphrases for repeated traffic.
- Fuse with deterministic rules first; learned re-rankers come later once offline labels exist.
- Emit rewritten queries in the retrieval trace so on-call engineers can debug surprising citations.
