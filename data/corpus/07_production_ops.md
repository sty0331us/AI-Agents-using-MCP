---
title: Production RAG Operations
topic: ops
level: beginner
module: course-module-2
---

# Production RAG Operations

Shipping RAG is more than wiring LangChain components.

## Non-negotiables

- Structured request IDs across retrieve and generate spans.
- Deterministic config via environment variables (embedding model, top_k, backends).
- Corpus versioning: every index build records corpus hash and chunk parameters.
- Graceful degradation: if the LLM rewrite path fails, fall back to plain vector retrieval.

## Frontend

A Gradio or internal admin UI is useful for strategy bake-offs, but customer traffic should hit a versioned HTTP API with schema-stable JSON responses.
