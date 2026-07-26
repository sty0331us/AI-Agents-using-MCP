"""MCP client exports."""

from clothes_recommend.clients.http_client import connect_remote_mcp
from clothes_recommend.clients.inprocess_client import connect_inprocess_mcp
from clothes_recommend.clients.stdio_client import connect_local_mcp

__all__ = [
    "connect_inprocess_mcp",
    "connect_local_mcp",
    "connect_remote_mcp",
]
