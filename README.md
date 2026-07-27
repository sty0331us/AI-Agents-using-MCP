# AI Agents Toolkit

Two production-oriented demos in one repository:

1. **RAG Retriever Comparison (`rag_compare`)** — compare vector, multi-query, self-query, and parent-document retrievers on FAISS or Chroma with latency / hit-rate / MRR reporting, FastAPI, and Gradio.
2. **Clothes Recommend System (`clothes_recommend`)** — weather-aware outfit recommendations over FastMCP (local STDIO + remote Streamable HTTP).

---

## RAG Retriever Comparison

Portfolio-ready, production-shaped code for proving retrieval strategy tradeoffs to hiring managers — not a notebook toy.

### What it demonstrates

| Strategy | Production intent |
|---|---|
| **Vector store retriever** | Low-latency dense NN baseline |
| **Multi-query retriever** | LLM paraphrase expansion → higher recall, higher cost |
| **Self-querying retriever** | NL → semantic query + metadata filters (with empty-result fallback) |
| **Parent-document retriever** | Search child chunks, return parent context for generation |

Backends: **FAISS** (in-process cosine/IP) and **Chroma** (persistent collections + metadata `where` filters).

### Architecture

```text
Corpus (md) ──► parent/child chunking ──► Embedder ──► FAISS | Chroma
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
              VectorRetriever          MultiQueryRetriever        SelfQueryRetriever
                    │                         │                         │
                    └─────────────► ParentDocumentRetriever ◄───────────┘
                                              │
                              Compare harness (p50/p95, hit@k, MRR)
                                              │
                              FastAPI  (/retrieve /compare /answer)
                              Gradio UI (strategy bake-off)
```

### Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export PYTHONPATH=src

# Build index + compare all strategies (works offline with hash embeddings)
python -m rag_compare.cli --vector-backend faiss compare

# Single retrieval with trace
python -m rag_compare.cli retrieve \
  --query "advanced parent document retrieval" \
  --strategy parent_document

# FastAPI
python -m rag_compare.cli api
# POST http://127.0.0.1:8090/ingest  {"vector_backend":"faiss"}
# POST http://127.0.0.1:8090/compare {"queries":["Compare FAISS and Chroma"]}

# Gradio UI
python -m rag_compare.cli ui
```

Offline defaults (`EMBEDDING_BACKEND=hash`, `LLM_BACKEND=heuristic`) run without API keys so recruiters can clone and execute immediately. Set `EMBEDDING_BACKEND=openai` / `LLM_BACKEND=openai` plus `OPENAI_API_KEY` for semantic + LLM-quality rewrites.

### API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness + ingest status |
| `POST` | `/ingest` | Chunk corpus, build index (`faiss` \| `chroma`) |
| `POST` | `/retrieve` | Run one strategy with full retrieval trace |
| `POST` | `/compare` | Side-by-side metrics for all strategies |
| `POST` | `/answer` | Retrieve + grounded generation |

### Layout

```text
src/rag_compare/
  config.py              # pydantic-settings
  embeddings.py          # hash | openai | sentence-transformers
  llm.py                 # heuristic | openai
  models.py              # Document, RetrievalResult, ComparisonReport
  stores/                # FAISS + Chroma
  retrievers/            # four strategies + factory
  pipeline/              # ingest, compare, RAG answer
  evaluation/            # hit@k, MRR, latency percentiles
  service.py             # thread-safe app service
  api/app.py             # FastAPI
  ui/gradio_app.py       # Gradio bake-off UI
  cli.py
data/corpus/             # sample knowledge base
data/eval/queries.txt
tests/test_rag_compare.py
```

### Tests

```bash
export PYTHONPATH=src
pytest -q
```

---

## Clothes Recommend System (FastMCP)

Weather-aware clothing recommendations delivered through **FastMCP**.

The system resolves a place name, fetches **today’s live weather**, and returns a structured **outfit recommendation**. MCP Host and Client communicate with MCP servers using **JSON-RPC 2.0** messages over:

1. **Local MCP server** — STDIO transport (`servers/local_stdio/server.py`)
2. **Remote MCP server** — Streamable HTTP transport (`servers/remote_http/server.py`)

An **MCP Host (Web Client)** inherits the shared `McpClient` class so the browser UI and API reuse the same client logic as the CLI.

### Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│              MCP Host (Web Client) · McpHostApp                  │
│              inherits McpClient                                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │ uses / inherits
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                         McpClient                                │
│              FastMCP Client · tools/list · tools/call            │
└────────────────────┬──────────────────────────┬──────────────────┘
                     │                          │
                     │ JSON-RPC 2.0             │ JSON-RPC 2.0
                     │ over STDIO               │ over Streamable HTTP
                     ▼                          ▼
┌────────────────────────────────┐  ┌──────────────────────────────┐
│ Local FastMCP server           │  │ Remote FastMCP server        │
│ clothes-recommend-local        │  │ clothes-recommend-remote     │
│ servers/local_stdio/server.py  │  │ servers/remote_http/server.py│
└───────────────┬────────────────┘  └──────────────┬───────────────┘
                │                                  │
                └────────────────┬─────────────────┘
                                 ▼
              create_clothes_mcp() + domain services
              Open-Meteo weather · clothing rules
```

### Run (clothes)

```bash
export PYTHONPATH=src
uvicorn clothes_recommend.host.app:app --host 127.0.0.1 --port 8080
python -m clothes_recommend.main local --location "Seoul"
```

Requires **Python 3.10+** and outbound HTTPS access to Open-Meteo for the clothes demo.

---

## License

MIT
