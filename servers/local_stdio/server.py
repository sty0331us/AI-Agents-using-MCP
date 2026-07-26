"""
Local MCP server — STDIO transport.

The host (our agent client) launches this file as a subprocess and
communicates over stdin/stdout. Do not print debug logs to stdout;
they would corrupt the JSON-RPC stream. Use stderr if you need logging.

Run standalone (for Inspector / manual testing)::

    python servers/local_stdio/server.py
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("local-demo")


@mcp.tool()
def echo(message: str) -> str:
    """Echo a message back to the caller."""
    return f"[local] {message}"


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@mcp.resource("note://local")
def local_note() -> str:
    """A sample resource from the local STDIO server."""
    return "This resource is served by the local STDIO MCP server."


if __name__ == "__main__":
    # Default FastMCP transport is stdio.
    mcp.run(transport="stdio")
