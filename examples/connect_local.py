"""
Minimal example: connect to the local MCP server via STDIO.

From the repository root::

    PYTHONPATH=src python examples/connect_local.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp_agent.clients import connect_local_mcp
from mcp_agent.clients.base import call_tool_text, list_tool_names


async def main() -> None:
    async with connect_local_mcp() as session:
        print("Connected to local MCP (STDIO)")
        print("Tools:", await list_tool_names(session))
        print("echo:", await call_tool_text(session, "echo", {"message": "hi"}))


if __name__ == "__main__":
    asyncio.run(main())
