"""
Clothes Recommend System — local MCP server (STDIO).

Exposes weather lookup and clothing recommendation tools. Desktop hosts launch
this process and speak MCP over stdin/stdout.

Run::

    python servers/local_stdio/server.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from clothes_recommend.mcp_tools.server_factory import create_clothes_mcp

mcp = create_clothes_mcp(name="clothes-recommend-local")


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
