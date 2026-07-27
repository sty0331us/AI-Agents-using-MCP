---
title: Self-Querying Retrievers
topic: retrieval
level: advanced
module: course-module-1
---

# Self-Querying Retrievers

A self-querying retriever decomposes natural language into a semantic query plus structured metadata filters (topic, level, tenant, document type).

## Example

User: "Show advanced material about vector databases"

Plan:

- semantic query: "vector databases"
- filter: `{ "level": "advanced", "topic": "vector_db" }`

## Production guardrails

- Constrain allowed filter keys; never let the LLM invent arbitrary operators against production indexes.
- Soft-fallback to unconstrained search when filters return empty results, and flag the fallback in traces.
- Validate extracted values against an allow-list (enums) before hitting Chroma/FAISS metadata predicates.
