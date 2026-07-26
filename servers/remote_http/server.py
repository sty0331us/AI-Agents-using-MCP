"""
Clothes Recommend System — remote MCP runtime (Streamable HTTP).

Long-lived networked service for VPC / container / API-gateway deployments.
Bind address, path, and stateless mode are controlled by environment variables
so the same image can run behind AWS ALB/API Gateway or Azure App Gateway/APIM.

Entrypoint::

    python servers/remote_http/server.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from clothes_recommend.config import get_settings
from clothes_recommend.mcp_tools.server_factory import create_clothes_mcp

settings = get_settings()
mcp = create_clothes_mcp(
    name="clothes-recommend-remote",
    include_ops_routes=True,
)


if __name__ == "__main__":
    run_kwargs: dict = {
        "transport": "http",
        "host": settings.remote_mcp_host,
        "port": settings.remote_mcp_port,
        "path": settings.remote_mcp_path,
        "stateless_http": settings.remote_mcp_stateless_http,
        "log_level": settings.remote_mcp_log_level,
        "show_banner": False,
    }
    if settings.allowed_hosts_list is not None:
        run_kwargs["allowed_hosts"] = settings.allowed_hosts_list
    if settings.allowed_origins_list is not None:
        run_kwargs["allowed_origins"] = settings.allowed_origins_list

    mcp.run(**run_kwargs)
