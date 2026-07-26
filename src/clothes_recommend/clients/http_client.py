"""Remote FastMCP client (Streamable HTTP) — cloud gateway compatible."""

from __future__ import annotations

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from clothes_recommend.config import get_settings


def build_remote_headers(
    auth_token: str | None = None,
    api_key: str | None = None,
) -> dict[str, str] | None:
    """
    Build headers for API Gateway, Azure APIM, or other edge auth.

    - Authorization: Bearer <token>  (OIDC / Cognito / Entra ID style)
    - x-api-key: <key>               (API Gateway / APIM subscription key)
    """
    settings = get_settings()
    token = auth_token if auth_token is not None else settings.remote_mcp_auth_token
    key = api_key if api_key is not None else settings.remote_mcp_api_key

    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if key:
        headers["x-api-key"] = key
    return headers or None


def build_http_transport(
    url: str | None = None,
    auth_token: str | None = None,
    api_key: str | None = None,
) -> StreamableHttpTransport:
    settings = get_settings()
    target = url or settings.remote_mcp_url
    headers = build_remote_headers(auth_token=auth_token, api_key=api_key)
    return StreamableHttpTransport(url=target, headers=headers)


def connect_remote_mcp(
    url: str | None = None,
    auth_token: str | None = None,
    api_key: str | None = None,
) -> Client:
    """
    Return a FastMCP Client for the remote Clothes Recommend HTTP service.

    Point ``url`` (or ``REMOTE_MCP_URL``) at the public or private endpoint
    fronted by a load balancer or API gateway in AWS / Azure.
    """
    return Client(
        build_http_transport(url=url, auth_token=auth_token, api_key=api_key)
    )
