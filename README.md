# AI Agents using MCP

Python project structure for connecting an AI agent to:

1. **Local MCP servers** via **STDIO** transport  
2. **Remote MCP servers** via **Streamable HTTP** transport  

Built on the official [`mcp`](https://github.com/modelcontextprotocol/python-sdk) Python SDK (stable **v1.x**).

---

## How the system connects

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Your AI Agent                            │
│                  (src/mcp_agent/agent/runner.py)                │
└───────────────┬─────────────────────────────┬───────────────────┘
                │                             │
                │  STDIO                      │  Streamable HTTP
                │  (spawn subprocess)         │  (connect to URL)
                ▼                             ▼
┌───────────────────────────┐   ┌─────────────────────────────────┐
│  Local MCP Server         │   │  Remote MCP Server              │
│  servers/local_stdio/     │   │  servers/remote_http/           │
│                           │   │                                 │
│  Client launches process  │   │  Server already listening on    │
│  JSON-RPC on stdin/stdout │   │  http://host:port/mcp           │
└───────────────────────────┘   └─────────────────────────────────┘
```

| | **Local (STDIO)** | **Remote (Streamable HTTP)** |
|---|---|---|
| **When** | Server runs on the same machine; one client owns the process | Server is networked, hosted, or shared by many clients |
| **Who starts the server** | The **client** spawns it | You (or a platform) start it separately |
| **How bytes move** | Child process stdin / stdout | HTTP POST (+ optional SSE stream) to `/mcp` |
| **Client code** | `connect_local_mcp()` | `connect_remote_mcp()` |
| **Config** | `LOCAL_MCP_COMMAND` / `LOCAL_MCP_ARGS` | `REMOTE_MCP_URL` (+ optional auth token) |

> **Note:** Older **HTTP+SSE** transport is legacy. Prefer **Streamable HTTP** for all new remote servers.

---

## Repository layout

```text
AI-Agents-using-MCP/
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example                 # Copy to .env and edit
├── config/
│   └── servers.yaml             # Human-readable server registry
├── src/
│   └── mcp_agent/
│       ├── config.py            # Env-based settings
│       ├── main.py              # CLI: local | remote | both
│       ├── agent/
│       │   └── runner.py        # Demo flows for both transports
│       └── clients/
│           ├── base.py          # Shared list/call helpers
│           ├── stdio_client.py  # Local MCP (STDIO)
│           └── http_client.py   # Remote MCP (Streamable HTTP)
├── servers/
│   ├── local_stdio/
│   │   └── server.py            # Example local server (stdio)
│   └── remote_http/
│       └── server.py            # Example remote server (streamable-http)
└── examples/
    ├── connect_local.py         # Minimal STDIO client
    └── connect_remote.py        # Minimal HTTP client
```

### Responsibility of each layer

| Layer | Role |
|---|---|
| `clients/` | Open a protocol session over the right transport |
| `agent/` | Use sessions (list tools, call tools) — your agent logic lives here |
| `servers/` | Example MCP servers that expose tools/resources |
| `config/` + `.env` | Declare *where* servers live without hard-coding URLs in code |
| `examples/` | Small scripts that show one connection style at a time |

---

## Prerequisites

- **Python 3.10+** (required by the MCP SDK)
- `pip` or `uv`

```bash
git clone https://github.com/sty0331us/AI-Agents-using-MCP.git
cd AI-Agents-using-MCP

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
# or: pip install -e .

cp .env.example .env
```

Set `PYTHONPATH` so imports resolve from `src/` (or install the package editable):

```bash
export PYTHONPATH=src
```

---

## 1) Local MCP — STDIO transport

### Idea

Your agent **starts** the server process and talks JSON-RPC on the child’s **stdin/stdout**. When the client exits, the subprocess is shut down.

### Example server

`servers/local_stdio/server.py` exposes:

- tool `echo(message)`
- tool `add(a, b)`
- resource `note://local`

### Connect from the agent

```python
from mcp_agent.clients import connect_local_mcp

async with connect_local_mcp() as session:
    tools = await session.list_tools()
    result = await session.call_tool("echo", {"message": "hello"})
```

Under the hood (`src/mcp_agent/clients/stdio_client.py`):

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(
    command="python",
    args=["servers/local_stdio/server.py"],
)

async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        # use session...
```

### Run

```bash
# From repo root
export PYTHONPATH=src
python examples/connect_local.py
# or
python -m mcp_agent.main local
```

No separate server terminal is needed — the client spawns it.

---

## 2) Remote MCP — Streamable HTTP transport

### Idea

The server is an **HTTP process** already listening on a port. Your agent connects with a **URL** (for example `http://localhost:8000/mcp`). Many clients can share one server.

### Example server

`servers/remote_http/server.py` exposes:

- tool `weather(city)`
- tool `add(a, b)`
- resource `note://remote`

### Start the remote server

```bash
export PYTHONPATH=src
python servers/remote_http/server.py
# listens on http://127.0.0.1:8000/mcp
```

### Connect from the agent

```python
from mcp_agent.clients import connect_remote_mcp

async with connect_remote_mcp("http://localhost:8000/mcp") as session:
    tools = await session.list_tools()
    result = await session.call_tool("weather", {"city": "Seoul"})
```

Under the hood (`src/mcp_agent/clients/http_client.py`):

```python
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async with httpx.AsyncClient(follow_redirects=True) as http:
    async with streamable_http_client(
        "http://localhost:8000/mcp",
        http_client=http,
    ) as (read, write, _session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # use session...
```

Optional Bearer auth (set `REMOTE_MCP_AUTH_TOKEN` in `.env`, or pass it in):

```python
async with connect_remote_mcp(
    url="https://mcp.example.com/mcp",
    auth_token="your-token",
) as session:
    ...
```

> Host, port, and `/mcp` path for the example remote server are set on `FastMCP(...)` in `servers/remote_http/server.py`, then started with `mcp.run(transport="streamable-http")`.

### Run

```bash
# Terminal A — server
python servers/remote_http/server.py

# Terminal B — client
export PYTHONPATH=src
python examples/connect_remote.py
# or
python -m mcp_agent.main remote
```

---

## 3) Use both in one agent

```bash
# Terminal A
python servers/remote_http/server.py

# Terminal B
export PYTHONPATH=src
python -m mcp_agent.main both
```

`runner.py` opens a STDIO session for local tools, then an HTTP session for remote tools. In a real agent you would:

1. Discover tools from each session (`list_tools`)
2. Let the LLM choose a tool
3. Route the call to the correct session (local vs remote)

---

## Configuration

Copy `.env.example` → `.env`:

```bash
LOCAL_MCP_COMMAND=python
LOCAL_MCP_ARGS=servers/local_stdio/server.py

REMOTE_MCP_URL=http://localhost:8000/mcp
REMOTE_MCP_AUTH_TOKEN=
```

`config/servers.yaml` documents the same registry in YAML for humans / future multi-server loading.

---

## Choosing a transport

```text
Is the MCP server on the same machine and owned by one client?
├── Yes → STDIO (local)
└── No  → Streamable HTTP (remote / shared / cloud)
```

| Prefer **STDIO** when… | Prefer **Streamable HTTP** when… |
|---|---|
| Desktop / IDE host launches tools | Server runs in Docker / cloud / another host |
| You want no ports or auth ceremony | Multiple agents must share one server |
| Lifetime of server = lifetime of client | You need auth, load balancers, HTTPS |

---

## Extending this structure

1. **Add a tool** on a server under `servers/*/server.py` with `@mcp.tool()`.
2. **Add another remote host** by setting `REMOTE_MCP_URL` or calling `connect_remote_mcp(url=...)`.
3. **Wire an LLM** in `agent/runner.py`: pass `list_tools()` schemas to the model, then `call_tool()` on the matching session.
4. **Register more servers** in `config/servers.yaml` and load them in a small factory next to `clients/`.

---

## License

MIT
