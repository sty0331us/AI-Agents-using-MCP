# Clothes Recommend System

Enterprise clothing-recommendation service built on the **Model Context Protocol (MCP)** and **FastMCP**.

Given a geographic location, the system retrieves **live weather conditions** and returns a **structured outfit recommendation** (base layers, outerwear, footwear, accessories, and exclusions). Domain logic is shared; capability exposure is standardized through MCP so desktop agents, backend workers, and remote services consume the same contracts.

---

## System overview

| Capability | Detail |
|---|---|
| Product | Location-aware outfit recommendation |
| Protocol | MCP over FastMCP |
| Weather provider | Open-Meteo (geocoding + current conditions) |
| Recommendation engine | Deterministic rules on temperature band + WMO weather code |
| Deployment modes | Edge/local STDIO process · networked Streamable HTTP service |

---

## Deployment topology

Production workloads attach to MCP through one of two transports, chosen by runtime environment—not by ad-hoc scripting.

```text
┌──────────────────────────────────────────────────────────────────┐
│              Clothes Recommend System (orchestrator)             │
│                         FastMCP Client                           │
└────────────────────┬──────────────────────────┬──────────────────┘
                     │                          │
                     │ STDIO                    │ Streamable HTTP
                     │ process lifecycle        │ service endpoint
                     ▼                          ▼
┌────────────────────────────────┐  ┌──────────────────────────────┐
│ Local MCP runtime              │  │ Remote MCP runtime           │
│ clothes-recommend-local        │  │ clothes-recommend-remote     │
│ servers/local_stdio/server.py  │  │ servers/remote_http/server.py│
│ Transport: STDIO               │  │ Transport: Streamable HTTP   │
└───────────────┬────────────────┘  └──────────────┬───────────────┘
                │                                  │
                └────────────────┬─────────────────┘
                                 ▼
                    Shared application core
                    create_clothes_mcp() · domain/
                    weather client · clothing policy
```

| Dimension | **Local MCP** | **Remote MCP** |
|---|---|---|
| Framework | FastMCP | FastMCP |
| Transport | STDIO | Streamable HTTP |
| Process model | Orchestrator-managed child process (stdin/stdout) | Independently deployed HTTP service |
| Typical placement | Desktop agents, IDE hosts, on-device workers | VPC / container / API gateway–fronted service |
| Addressing | Command + args from configuration | Service URL (`REMOTE_MCP_URL`) |
| Client API | `connect_local_mcp()` | `connect_remote_mcp()` |

**Local STDIO** fits tightly coupled runtimes where the host owns process lifecycle, isolation, and teardown.  
**Remote Streamable HTTP** fits multi-client, horizontally scaled, or cross-network access with standard HTTP operational controls (health checks, auth headers, load balancing).

Both runtimes register identical tools through `create_clothes_mcp()`, so clients remain transport-agnostic at the tool layer.

---

## Delivery phases

| Phase | Scope | Outcome |
|---|---|---|
| **1 · Domain core** | Weather client, WMO mapping, clothing policy, Pydantic models | Deterministic recommendation logic independent of transport |
| **2 · MCP contract** | Shared tool registration | Stable capability surface for any MCP-compatible consumer |
| **3 · Local runtime** | FastMCP STDIO server + orchestrator client | Edge / desktop integration with managed process lifecycle |
| **4 · Remote runtime** | FastMCP Streamable HTTP + `/health` `/ready` | Networked service ready for load balancers and gateways |
| **5 · Horizontal scale** | `REMOTE_MCP_STATELESS_HTTP`, bind `0.0.0.0`, env-driven URLs/keys | Multi-instance deployment behind AWS / Azure edge |
| **6 · Cloud edge** | ALB / API Gateway / App Gateway / APIM + secrets + observability | Enterprise ingress, auth, and operations |

---

## MCP tool contract

| Tool | Contract |
|---|---|
| `get_location_weather` | Resolve a place name; return current temperature, humidity, wind, precipitation, and WMO weather code |
| `recommend_clothes` | Produce an outfit from temperature, weather code, and optional apparent temperature / wind / humidity |
| `recommend_clothes_for_location` | Compose weather retrieval and recommendation in a single tool invocation |

Prefer `recommend_clothes_for_location` when the caller only has a location string; use the split tools when weather is already available upstream.

---

## Cloud scalability (remote MCP)

When traffic is served through the **remote Streamable HTTP** runtime, place it behind standard cloud edge and compute services. The application is written for that model: **stateless HTTP** (default), **container-friendly bind** (`0.0.0.0`), **health probes**, and **gateway-compatible client headers**.

```text
                         Clients / orchestrators
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
   AWS API Gateway          Azure API Management     Direct VPC / Private Link
   (HTTP API + WAF)         (APIM + policies)        (internal only)
            │                       │                       │
            └───────────┬───────────┴───────────┬───────────┘
                        ▼                       ▼
              AWS Application LB          Azure Application Gateway
              (health: GET /health)       / Front Door (GET /health)
                        │                       │
                        ▼                       ▼
              ECS Fargate / EKS           Container Apps / AKS
              clothes-recommend-remote    clothes-recommend-remote
              FastMCP · Streamable HTTP   FastMCP · Streamable HTTP
              REMOTE_MCP_STATELESS_HTTP   REMOTE_MCP_STATELESS_HTTP
```

### Why this shape scales

| Concern | Application support | Cloud control plane |
|---|---|---|
| Multiple replicas | `REMOTE_MCP_STATELESS_HTTP=true` — no sticky sessions required | ALB / NLB target groups · App Gateway backend pools · K8s Services |
| Health checking | `GET /health`, `GET /ready` on the remote runtime | ALB/NLB health checks · Azure probes · Kubernetes liveness/readiness |
| Public or partner ingress | Client uses `REMOTE_MCP_URL` | API Gateway · Azure APIM · Front Door |
| AuthN / AuthZ | `Authorization: Bearer …`, `x-api-key` | Cognito / IAM · Entra ID · API keys / APIM subscriptions · WAF |
| Secrets | Env / `.env` mapped at deploy time | AWS Secrets Manager / SSM · Azure Key Vault |
| TLS | Terminated at edge (recommended) | ACM · Azure Key Vault certificates |
| Observability | Structured service name on probes; app logs via uvicorn | CloudWatch · X-Ray · Azure Monitor · Application Insights |
| Network isolation | Private listen + edge only | VPC private subnets · Azure VNet + Private Link |

Reference inventory: `config/cloud.yaml`.

### AWS reference stack

| Layer | Services | Role |
|---|---|---|
| Compute | **Amazon ECS on Fargate**, **EKS**, or **App Runner** | Run `servers/remote_http/server.py` as replicated tasks/pods |
| Load balancing | **Application Load Balancer** (L7) or **Network Load Balancer** | Distribute MCP traffic; probe `/health` |
| API edge | **Amazon API Gateway** (HTTP API) | Throttling, API keys, JWT authorizers, WAF association |
| Security | **AWS WAF**, **ACM**, **Secrets Manager**, **Cognito** | Edge protection, TLS, secret injection, Bearer tokens |
| Networking | **VPC**, private subnets, **Cloud Map** / Route 53 | Private service discovery; no public task IPs required |
| Ops | **CloudWatch** Logs/Metrics/Alarms, **X-Ray** | SLOs, dashboards, tracing |

**Client configuration against AWS**

```bash
# After ALB or API Gateway is provisioned:
REMOTE_MCP_URL=https://mcp.example.com/mcp
REMOTE_MCP_AUTH_TOKEN=<cognito-or-jwt-access-token>
REMOTE_MCP_API_KEY=<api-gateway-key>   # optional, if API keys are enabled
```

### Azure reference stack

| Layer | Services | Role |
|---|---|---|
| Compute | **Azure Container Apps**, **AKS**, or **App Service** | Host the remote FastMCP runtime at scale |
| Load balancing | **Application Gateway**, **Azure Front Door** | Global or regional L7 entry; probe `/health` |
| API edge | **Azure API Management (APIM)** | Subscriptions, rate limits, policies, `x-api-key` |
| Security | **Microsoft Entra ID**, **Key Vault**, **WAF** | Bearer tokens, secrets, edge filtering |
| Networking | **Virtual Network**, Private Endpoints | Isolate backends from the public internet |
| Ops | **Azure Monitor**, **Application Insights** | Metrics, logs, distributed tracing |

**Client configuration against Azure**

```bash
REMOTE_MCP_URL=https://mcp.contoso.com/mcp
REMOTE_MCP_AUTH_TOKEN=<entra-id-access-token>
REMOTE_MCP_API_KEY=<apim-subscription-key>
```

### Scaling checklist (remote path)

1. Build/run the remote image with `REMOTE_MCP_HOST=0.0.0.0` and `REMOTE_MCP_STATELESS_HTTP=true`.
2. Register target health checks on **`/health`** (liveness) and optionally **`/ready`**.
3. Put **2+** tasks/replicas behind ALB / App Gateway / a Kubernetes Service.
4. Front with **API Gateway** or **APIM** when you need partner auth, quotas, or WAF.
5. Point orchestrators at the edge URL via **`REMOTE_MCP_URL`** (never hard-code instance IPs).
6. Store tokens and API keys in **Secrets Manager** / **Key Vault**; inject as env vars at deploy time.

Local STDIO remains the edge/desktop path and does not sit behind cloud load balancers; scale cloud traffic on the **remote** runtime only.

---

## Repository structure

```text
AI-Agents-using-MCP/
├── src/clothes_recommend/
│   ├── domain/                 # weather provider client, clothing policy
│   ├── mcp_tools/
│   │   ├── server_factory.py   # FastMCP server construction
│   │   ├── ops_routes.py       # /health · /ready for cloud probes
│   │   └── __init__.py         # tool registration
│   ├── clients/
│   │   ├── stdio_client.py     # local MCP client (STDIO)
│   │   └── http_client.py      # remote MCP client (Bearer + x-api-key)
│   ├── agent/runner.py
│   ├── config.py               # env settings including cloud bind/auth
│   └── main.py
├── servers/
│   ├── local_stdio/server.py   # FastMCP STDIO runtime
│   └── remote_http/server.py   # FastMCP HTTP · stateless · ops routes
├── config/
│   ├── servers.yaml            # MCP endpoint registry
│   └── cloud.yaml              # AWS / Azure reference topology
└── examples/
```

---

## Environment bootstrap

```bash
git clone https://github.com/sty0331us/AI-Agents-using-MCP.git
cd AI-Agents-using-MCP

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
export PYTHONPATH=src
```

Runtime requirements: **Python 3.10+**, outbound HTTPS to Open-Meteo, and (for remote mode) a reachable Streamable HTTP MCP endpoint.

---

## Operations

### Local MCP (STDIO)

The orchestrator starts the local FastMCP runtime as a managed subprocess and communicates over STDIO for the duration of the session:

```bash
python -m clothes_recommend.main local --location "Seoul"
```

### Remote MCP (Streamable HTTP)

Run the remote runtime as a service process (locally, under systemd, or as a container task). In cloud environments the same process listens on `0.0.0.0` and is registered with a load balancer or API gateway:

```bash
python servers/remote_http/server.py
# probes:  GET /health   GET /ready
# mcp:     POST/GET {REMOTE_MCP_PATH}  (default /mcp)

python -m clothes_recommend.main remote --location "Tokyo"
```

Set `REMOTE_MCP_URL` to the ALB, API Gateway, App Gateway, or APIM URL in staging and production.

### Dual-transport execution

```bash
python -m clothes_recommend.main both --location "London"
```

---

## Integration (client SDK)

```python
from clothes_recommend.clients import connect_local_mcp, connect_remote_mcp

async with connect_local_mcp() as client:
    result = await client.call_tool(
        "recommend_clothes_for_location",
        {"location": "Seoul"},
    )

# Points at REMOTE_MCP_URL (gateway / load balancer in cloud)
async with connect_remote_mcp() as client:
    result = await client.call_tool(
        "recommend_clothes_for_location",
        {"location": "Tokyo"},
    )
```

---

## Configuration

| Variable | Role | Default |
|---|---|---|
| `DEFAULT_LOCATION` | Default location for CLI invocations | `Seoul` |
| `LOCAL_MCP_COMMAND` | Executable for the STDIO runtime | `python` |
| `LOCAL_MCP_ARGS` | Local server module arguments | `servers/local_stdio/server.py` |
| `REMOTE_MCP_URL` | Client URL (localhost or cloud edge) | `http://localhost:8000/mcp` |
| `REMOTE_MCP_AUTH_TOKEN` | Bearer token (Cognito / Entra ID) | _(unset)_ |
| `REMOTE_MCP_API_KEY` | API Gateway / APIM key (`x-api-key`) | _(unset)_ |
| `REMOTE_MCP_HOST` | Server bind address | `0.0.0.0` |
| `REMOTE_MCP_PORT` | Server port | `8000` |
| `REMOTE_MCP_PATH` | MCP path | `/mcp` |
| `REMOTE_MCP_STATELESS_HTTP` | Horizontal-scale safe mode | `true` |
| `REMOTE_MCP_LOG_LEVEL` | Uvicorn/FastMCP log level | `INFO` |
| `REMOTE_MCP_ALLOWED_HOSTS` | Optional Host allow-list (CSV) | _(unset)_ |
| `REMOTE_MCP_ALLOWED_ORIGINS` | Optional CORS origins (CSV) | _(unset)_ |

See also `config/servers.yaml` and `config/cloud.yaml`.

---

## Engineering principles

- **Transport isolation** — STDIO and Streamable HTTP are first-class runtimes; domain logic does not depend on either.
- **Contract parity** — both servers expose the same tool schema via a single factory.
- **Stateless remote path** — default configuration supports load-balanced replicas without session affinity.
- **Edge-ready auth** — Bearer and API-key headers map cleanly to AWS API Gateway and Azure APIM.
- **Probeable service** — `/health` and `/ready` support cloud and Kubernetes health models.
- **Provider discipline** — Open-Meteo access is confined to `WeatherService` with connection pooling and a short TTL cache.

---

## License

MIT
