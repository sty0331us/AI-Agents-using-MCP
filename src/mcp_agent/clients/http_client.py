"""
Remote MCP client using Streamable HTTP transport.

The client connects to an already-running MCP server at a URL.
Use this for hosted / networked servers (cloud, another machine, or a
local process that you started separately on a port).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from mcp_agent.config import get_settings


def _build_headers(auth_token: str | None) -> dict[str, str]:
    if not auth_token:
        return {}
    return {"Authorization": f"Bearer {auth_token}"}


@asynccontextmanager
async def connect_remote_mcp(
    url: str | None = None,
    auth_token: str | None = None,
    timeout: float = 30.0,
    read_timeout: float = 300.0,
) -> AsyncIterator[ClientSession]:
    """
    Open a ClientSession to a remote MCP server over Streamable HTTP.

    Auth, timeouts, and other HTTP options belong on an ``httpx.AsyncClient``
    (the SDK's ``streamable_http_client`` does not take ``headers=`` directly).

    Usage::

        async with connect_remote_mcp("http://localhost:8000/mcp") as session:
            tools = await session.list_tools()
    """
    settings = get_settings()
    target = url or settings.remote_mcp_url
    token = auth_token if auth_token is not None else settings.remote_mcp_auth_token
    headers = _build_headers(token)

    async with httpx.AsyncClient(
        headers=headers,
        timeout=httpx.Timeout(timeout, read=read_timeout),
        follow_redirects=True,
    ) as http_client:
        async with streamable_http_client(
            target,
            http_client=http_client,
        ) as (read_stream, write_stream, _get_session_id):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session


# Alias kept for clarity in docs / imports
connect_remote_mcp_with_httpx = connect_remote_mcp
