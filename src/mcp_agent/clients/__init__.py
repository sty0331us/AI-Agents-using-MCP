"""Client package exports."""

from mcp_agent.clients.http_client import connect_remote_mcp
from mcp_agent.clients.stdio_client import connect_local_mcp

__all__ = [
    "connect_local_mcp",
    "connect_remote_mcp",
]
