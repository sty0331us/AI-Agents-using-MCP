"""
Class-based MCP client for Clothes Recommend System.

Wraps FastMCP transport helpers and exposes high-level operations that an
MCP Host (for example the web app) can inherit and reuse.
"""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import Client

from clothes_recommend.clients.base import call_tool_data, list_tool_names
from clothes_recommend.clients.http_client import connect_remote_mcp
from clothes_recommend.clients.stdio_client import connect_local_mcp

TransportName = Literal["local", "remote"]


class McpClient:
    """
    MCP Client facade.

    Opens a FastMCP session over STDIO (local) or Streamable HTTP (remote).
    Protocol messages between this client and MCP servers are exchanged as
    **JSON-RPC 2.0** payloads on top of the chosen transport.
    """

    def __init__(
        self,
        transport: TransportName = "local",
        *,
        remote_url: str | None = None,
        auth_token: str | None = None,
    ) -> None:
        self.transport: TransportName = transport
        self.remote_url = remote_url
        self.auth_token = auth_token

    def open_session(self) -> Client:
        """Return a FastMCP Client bound to the configured transport."""
        if self.transport == "local":
            return connect_local_mcp()
        return connect_remote_mcp(url=self.remote_url, auth_token=self.auth_token)

    async def list_tools(self) -> list[str]:
        async with self.open_session() as client:
            return await list_tool_names(client)

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Invoke an MCP tool (JSON-RPC ``tools/call`` under the hood)."""
        async with self.open_session() as client:
            return await call_tool_data(client, name, arguments)

    async def get_location_weather(self, location: str) -> Any:
        return await self.call_tool("get_location_weather", {"location": location})

    async def recommend_clothes_for_location(
        self,
        location: str,
        activity: str = "general",
    ) -> Any:
        return await self.call_tool(
            "recommend_clothes_for_location",
            {"location": location, "activity": activity},
        )
