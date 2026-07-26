# Clothes Recommend System

Weather-aware clothing recommendations delivered through **FastMCP**.

The system resolves a place name, fetches **today’s live weather**, and returns a structured **outfit recommendation**. Two separate FastMCP servers expose the same tools:

1. **Local MCP server** — STDIO transport (`servers/local_stdio/server.py`)  
2. **Remote MCP server** — Streamable HTTP transport (`servers/remote_http/server.py`)

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│                   Clothes Recommend System                       │
│                        FastMCP Client                            │
└────────────────────┬──────────────────────────┬──────────────────┘
                     │                          │
                     │ STDIO                    │ Streamable HTTP
                     │ (spawn subprocess)       │ (connect to URL)
                     ▼                          ▼
┌────────────────────────────────┐  ┌──────────────────────────────┐
│ Local FastMCP server           │  │ Remote FastMCP server        │
│ clothes-recommend-local        │  │ clothes-recommend-remote     │
│ servers/local_stdio/server.py  │  │ servers/remote_http/server.py│
│ transport: stdio               │  │ http://127.0.0.1:8000/mcp    │
└───────────────┬────────────────┘  └──────────────┬───────────────┘
                │                                  │
                └────────────────┬─────────────────┘
                                 ▼
              create_clothes_mcp() + domain services
              Open-Meteo weather · clothing rules
```

| | **Local MCP** | **Remote MCP** |
|---|---|---|
| Framework | FastMCP | FastMCP |
| Transport | STDIO | Streamable HTTP |
| Who starts the server | Client spawns the process | You start it separately |
| Endpoint | subprocess stdin/stdout | `http://127.0.0.1:8000/mcp` |
| Client helper | `connect_local_mcp()` | `connect_remote_mcp()` |

---

## MCP tools

Both servers register the same tools via `create_clothes_mcp()`:

| Tool | Purpose |
|---|---|
| `get_location_weather` | Geocode a place and return current weather |
| `recommend_clothes` | Outfit from temperature + WMO weather code |
| `recommend_clothes_for_location` | Weather + outfit in one call |

---

## Repository layout

```text
AI-Agents-using-MCP/
├── src/clothes_recommend/
│   ├── domain/                 # weather client, clothing engine
│   ├── mcp_tools/
│   │   ├── server_factory.py   # shared FastMCP server builder
│   │   └── __init__.py         # tool registration
│   ├── clients/
│   │   ├── stdio_client.py     # local FastMCP Client (STDIO)
│   │   └── http_client.py      # remote FastMCP Client (HTTP)
│   ├── agent/runner.py
│   └── main.py
├── servers/
│   ├── local_stdio/server.py   # FastMCP · STDIO
│   └── remote_http/server.py   # FastMCP · Streamable HTTP
└── examples/
    ├── connect_local.py
    └── connect_remote.py
```

---

## Setup

```bash
git clone https://github.com/sty0331us/AI-Agents-using-MCP.git
cd AI-Agents-using-MCP

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
export PYTHONPATH=src
```

Requires **Python 3.10+** and outbound HTTPS access to Open-Meteo.

---

## Run

### Local MCP (STDIO)

The client launches the FastMCP server as a subprocess:

```bash
python -m clothes_recommend.main local --location "Seoul"
# or
python examples/connect_local.py --location "Seoul"
```

### Remote MCP (Streamable HTTP)

```bash
# Terminal A — start the remote FastMCP server
python servers/remote_http/server.py

# Terminal B — connect over HTTP
python -m clothes_recommend.main remote --location "Tokyo"
# or
python examples/connect_remote.py --location "Tokyo"
```

### Both

```bash
python servers/remote_http/server.py   # Terminal A
python -m clothes_recommend.main both --location "London"   # Terminal B
```

---

## Client usage

```python
from clothes_recommend.clients import connect_local_mcp, connect_remote_mcp

# Local FastMCP · STDIO
async with connect_local_mcp() as client:
    result = await client.call_tool(
        "recommend_clothes_for_location",
        {"location": "Seoul"},
    )

# Remote FastMCP · Streamable HTTP
async with connect_remote_mcp("http://localhost:8000/mcp") as client:
    result = await client.call_tool(
        "recommend_clothes_for_location",
        {"location": "Tokyo"},
    )
```

Under the hood:

```python
# Local
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

client = Client(StdioTransport(command="python", args=["servers/local_stdio/server.py"]))

# Remote
from fastmcp.client.transports import StreamableHttpTransport

client = Client(StreamableHttpTransport(url="http://localhost:8000/mcp"))
```

---

## Configuration

| Variable | Description | Default |
|---|---|---|
| `DEFAULT_LOCATION` | Default place for CLI runs | `Seoul` |
| `LOCAL_MCP_COMMAND` | Interpreter for the STDIO server | `python` |
| `LOCAL_MCP_ARGS` | Local server script path | `servers/local_stdio/server.py` |
| `REMOTE_MCP_URL` | Remote MCP endpoint | `http://localhost:8000/mcp` |
| `REMOTE_MCP_AUTH_TOKEN` | Optional Bearer token | _(empty)_ |

---

## Design notes

- **Two servers only** — local STDIO and remote Streamable HTTP; both built with FastMCP.
- **Shared factory** — `create_clothes_mcp()` registers identical tools on both servers.
- **Structured outputs** — tools return JSON-serializable dicts for agents and APIs.

---

## License

MIT
