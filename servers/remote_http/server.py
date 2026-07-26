"""
Remote MCP server — Streamable HTTP transport.

This process listens on a TCP port. Clients connect with a URL such as
``http://localhost:8000/mcp``. Start it before running the remote client.

Run::

    python servers/remote_http/server.py
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "remote-demo",
    host="127.0.0.1",
    port=8000,
    streamable_http_path="/mcp",
    json_response=True,
)


@mcp.tool()
def weather(city: str) -> str:
    """Return a fake weather report for a city (demo only)."""
    return f"[remote] Weather in {city}: sunny, 22°C"


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@mcp.resource("note://remote")
def remote_note() -> str:
    """A sample resource from the remote HTTP server."""
    return "This resource is served by the remote Streamable HTTP MCP server."


if __name__ == "__main__":
    # Streamable HTTP is the recommended transport for networked / remote servers.
    # host / port / path are configured on FastMCP(...) above.
    mcp.run(transport="streamable-http")
