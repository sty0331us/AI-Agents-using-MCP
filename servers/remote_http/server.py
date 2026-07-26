"""
Clothes Recommend System — remote MCP server (Streamable HTTP).

Serves weather and clothing tools over HTTP for networked clients.

Run::

    python servers/remote_http/server.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from clothes_recommend.mcp_tools.server_factory import create_clothes_mcp

mcp = create_clothes_mcp(name="clothes-recommend-remote")


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000,
        path="/mcp",
        show_banner=False,
    )
