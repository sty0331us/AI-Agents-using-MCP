"""MCP client exports — local STDIO and remote Streamable HTTP only."""

from clothes_recommend.clients.http_client import connect_remote_mcp
from clothes_recommend.clients.stdio_client import connect_local_mcp

__all__ = [
    "connect_local_mcp",
    "connect_remote_mcp",
]
