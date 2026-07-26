"""Shared helpers for working with an open MCP ClientSession."""

from __future__ import annotations

from typing import Any

from mcp import ClientSession, types


async def list_tool_names(session: ClientSession) -> list[str]:
    """Return tool names exposed by the connected MCP server."""
    result = await session.list_tools()
    return [tool.name for tool in result.tools]


async def call_tool_text(
    session: ClientSession,
    name: str,
    arguments: dict[str, Any] | None = None,
) -> str:
    """Call a tool and return concatenated text content blocks."""
    result = await session.call_tool(name, arguments=arguments or {})
    if result.isError:
        messages = [
            block.text
            for block in result.content
            if isinstance(block, types.TextContent)
        ]
        raise RuntimeError(f"Tool {name!r} failed: {'; '.join(messages)}")

    texts: list[str] = []
    for block in result.content:
        if isinstance(block, types.TextContent):
            texts.append(block.text)

    if result.structuredContent is not None:
        return str(result.structuredContent)
    return "\n".join(texts)
