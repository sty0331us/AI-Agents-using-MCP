"""Remote FastMCP client (Streamable HTTP transport)."""

from __future__ import annotations

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from clothes_recommend.config import get_settings


def build_http_transport(
    url: str | None = None,
    auth_token: str | None = None,
) -> StreamableHttpTransport:
    settings = get_settings()
    target = url or settings.remote_mcp_url
    token = auth_token if auth_token is not None else settings.remote_mcp_auth_token
    headers = {"Authorization": f"Bearer {token}"} if token else None
    return StreamableHttpTransport(url=target, headers=headers)


def connect_remote_mcp(
    url: str | None = None,
    auth_token: str | None = None,
) -> Client:
    """Return a FastMCP Client for the remote Clothes Recommend HTTP server."""
    return Client(build_http_transport(url=url, auth_token=auth_token))
