"""Helpers for FastMCP Client results."""

from __future__ import annotations

from typing import Any

from fastmcp import Client


async def list_tool_names(client: Client) -> list[str]:
    tools = await client.list_tools()
    return [tool.name for tool in tools]


async def call_tool_data(
    client: Client,
    name: str,
    arguments: dict[str, Any] | None = None,
) -> Any:
    result = await client.call_tool(name, arguments=arguments or {})
    if result.is_error:
        raise RuntimeError(f"Tool {name!r} failed: {result.content}")
    if result.data is not None:
        return result.data
    if result.structured_content is not None:
        return result.structured_content
    return result.content
