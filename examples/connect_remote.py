"""
Minimal example: connect to a remote MCP server via Streamable HTTP.

Start the remote server first::

    PYTHONPATH=src python servers/remote_http/server.py

Then in another terminal::

    PYTHONPATH=src python examples/connect_remote.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp_agent.clients import connect_remote_mcp
from mcp_agent.clients.base import call_tool_text, list_tool_names


async def main() -> None:
    async with connect_remote_mcp() as session:
        print("Connected to remote MCP (Streamable HTTP)")
        print("Tools:", await list_tool_names(session))
        print(
            "weather:",
            await call_tool_text(session, "weather", {"city": "Seoul"}),
        )


if __name__ == "__main__":
    asyncio.run(main())
