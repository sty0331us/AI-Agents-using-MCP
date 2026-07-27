"""MCP client exports — local STDIO, remote Streamable HTTP, and class facade."""

from clothes_recommend.clients.http_client import connect_remote_mcp
from clothes_recommend.clients.mcp_client import McpClient
from clothes_recommend.clients.stdio_client import connect_local_mcp

__all__ = [
    "McpClient",
    "connect_local_mcp",
    "connect_remote_mcp",
]
