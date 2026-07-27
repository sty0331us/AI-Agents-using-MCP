---
title: Vector Store Retrievers
topic: retrieval
level: intermediate
module: course-module-1
---

# Vector Store-Backed Retrievers

A vector store-backed retriever embeds each corpus chunk and the user query into the same dense space, then returns the nearest neighbors by cosine similarity or inner product.

## Production notes

- Normalize embeddings when using inner-product indexes so scores behave like cosine similarity.
- Persist both vectors and document payloads; orphaned vectors without metadata break citation UX.
- Always record `latency_ms`, `top_k`, and backend name on every request for SLO dashboards.
- Start with a flat index (FAISS `IndexFlatIP`) until recall plateaus, then consider HNSW/IVF only with a recall evaluation harness.

## When it wins

Vector retrieval is the default low-latency path for clean semantic questions. It fails when users paraphrase with vocabulary the embedder maps poorly, which is why multi-query and self-query strategies exist.
