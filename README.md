# Clothes Recommend System

Weather-aware clothing recommendations delivered through **FastMCP**.

The system resolves a place name, fetches **today’s live weather**, and returns a structured **outfit recommendation** (layers, outerwear, footwear, accessories, and items to avoid). The same tool surface runs:

- **In-process** via FastMCP `Client(server)` — fastest local path  
- **Local STDIO** with subprocess **keep-alive** — for desktop MCP hosts  
- **Remote Streamable HTTP** — for networked deployments  

---

## Performance (FastMCP)

| Optimization | What it does |
|---|---|
| **In-process transport** | `Client(create_clothes_mcp())` talks to the server object in the same Python process — no STDIO spawn, no HTTP hop |
| **Single-tool fast path** | `recommend_clothes_for_location` returns weather + outfit in **one** MCP round-trip |
| **STDIO `keep_alive=True`** | Reuses the local subprocess across client contexts instead of respawning |
| **Shared HTTP pool + TTL cache** | Open-Meteo calls reuse one `httpx` client; weather is cached ~120s per place |
| **Concurrent `both`** | In-process + remote run with `asyncio.gather` |

Default CLI `local` uses the **in-process** FastMCP path. Use `stdio` when you need a real subprocess transport.

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│                   Clothes Recommend System                       │
│              FastMCP Client (in-process / STDIO / HTTP)          │
└───────────┬─────────────────────┬───────────────────┬────────────┘
            │                     │                   │
            │ in-process          │ STDIO keep-alive  │ Streamable HTTP
            ▼                     ▼                   ▼
┌────────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│ FastMCP server obj │  │ local_stdio      │  │ remote_http          │
│ (same process)     │  │ MCP server       │  │ MCP server :8000/mcp │
└─────────┬──────────┘  └────────┬─────────┘  └──────────┬───────────┘
          │                      │                       │
          └──────────────────────┴───────────────────────┘
                                 ▼
                   create_clothes_mcp() + domain/
                   Open-Meteo · clothing rules · TTL cache
```

| Concern | Implementation |
|---|---|
| Weather data | [Open-Meteo](https://open-meteo.com/) geocoding + forecast APIs |
| Recommendation logic | Deterministic rules on temperature band + WMO weather code |
| MCP framework | [FastMCP](https://gofastmcp.com) |
| Server factory | `clothes_recommend.mcp_tools.server_factory.create_clothes_mcp` |

---

## MCP tools

| Tool | Purpose |
|---|---|
| `recommend_clothes_for_location` | **Preferred** — weather + outfit in one call |
| `get_location_weather` | Geocode + current conditions only |
| `recommend_clothes` | Outfit from temperature / weather_code (when weather is already known) |

---

## Repository layout

```text
AI-Agents-using-MCP/
├── src/clothes_recommend/
│   ├── domain/                 # weather client (pooled HTTP + TTL cache), clothing engine
│   ├── mcp_tools/
│   │   ├── server_factory.py   # shared FastMCP server builder
│   │   └── __init__.py         # tool registration
│   ├── clients/
│   │   ├── inprocess_client.py # FastMCP Client(server) — fastest
│   │   ├── stdio_client.py     # STDIO + keep_alive
│   │   └── http_client.py      # Streamable HTTP
│   ├── agent/runner.py
│   └── main.py
├── servers/
│   ├── local_stdio/server.py
│   └── remote_http/server.py
└── examples/
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

```bash
# Fastest: in-process FastMCP
python -m clothes_recommend.main local --location "Seoul"

# STDIO subprocess with keep-alive
python -m clothes_recommend.main stdio --location "Seoul"

# Remote HTTP
python servers/remote_http/server.py          # terminal A
python -m clothes_recommend.main remote -l "Tokyo"   # terminal B

# Concurrent in-process + remote
python -m clothes_recommend.main both --location "London"
```

---

## Client usage

```python
from clothes_recommend.clients import connect_inprocess_mcp, connect_remote_mcp

# Fast local path
async with connect_inprocess_mcp() as client:
    result = await client.call_tool(
        "recommend_clothes_for_location",
        {"location": "Seoul"},
    )

# Remote
async with connect_remote_mcp("http://localhost:8000/mcp") as client:
    result = await client.call_tool(
        "recommend_clothes_for_location",
        {"location": "Tokyo"},
    )
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

- **Shared server factory** — in-process, STDIO, and HTTP all call `create_clothes_mcp()` so tools cannot drift.
- **Prefer one round-trip** — agents should call `recommend_clothes_for_location` unless they already hold weather fields.
- **Connection reuse** — process-wide `httpx` pool + weather TTL cache reduces provider latency under load.
- **Structured outputs** — tools return JSON-serializable dicts for agents and APIs.

---

## License

MIT
