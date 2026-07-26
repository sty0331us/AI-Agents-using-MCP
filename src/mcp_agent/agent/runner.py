"""
Agent runner that can talk to both local (STDIO) and remote (HTTP) MCP servers.
"""

from __future__ import annotations

from mcp_agent.clients import connect_local_mcp, connect_remote_mcp
from mcp_agent.clients.base import call_tool_text, list_tool_names


async def demo_local() -> None:
    """Connect to the local STDIO MCP server and exercise a tool."""
    print("=== Local MCP (STDIO) ===")
    async with connect_local_mcp() as session:
        tools = await list_tool_names(session)
        print(f"Tools: {tools}")
        if "echo" in tools:
            text = await call_tool_text(session, "echo", {"message": "hello from local"})
            print(f"echo -> {text}")
        if "add" in tools:
            text = await call_tool_text(session, "add", {"a": 2, "b": 3})
            print(f"add  -> {text}")


async def demo_remote() -> None:
    """Connect to the remote Streamable HTTP MCP server and exercise a tool."""
    print("=== Remote MCP (Streamable HTTP) ===")
    async with connect_remote_mcp() as session:
        tools = await list_tool_names(session)
        print(f"Tools: {tools}")
        if "weather" in tools:
            text = await call_tool_text(session, "weather", {"city": "Seoul"})
            print(f"weather -> {text}")
        if "add" in tools:
            text = await call_tool_text(session, "add", {"a": 10, "b": 32})
            print(f"add     -> {text}")


async def demo_both() -> None:
    """Run local then remote demos sequentially."""
    await demo_local()
    print()
    await demo_remote()
