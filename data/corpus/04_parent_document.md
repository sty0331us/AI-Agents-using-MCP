---
title: Parent Document Retrievers
topic: retrieval
level: advanced
module: course-module-1
---

# Parent Document Retrievers

Parent document retrieval indexes small child chunks for precise matching, then returns the larger parent passage to the generator.

## Why it matters in production

Tiny chunks improve embedding specificity. Large parents preserve discourse so the LLM does not invent bridges between fragmented sentences.

## Implementation checklist

- Stable `parent_id` on every child.
- Parent map must be rebuilt atomically with the child index.
- Over-fetch children (for example `top_k * 3`) before parent dedupe so the final context set still fills `top_k`.
- Prefer parent-level citations in the UI even when scoring happened on children.
