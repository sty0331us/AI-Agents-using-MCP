"""
Local MCP client using STDIO transport.

The client launches the MCP server as a subprocess and speaks JSON-RPC
over the child's stdin / stdout. Use this for servers that run on the
same machine as your agent.
"""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_agent.config import REPO_ROOT, get_settings


def build_stdio_params(
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> StdioServerParameters:
    """Build StdioServerParameters from settings or explicit overrides."""
    settings = get_settings()
    # Prefer the active interpreter so the child shares the same venv / deps.
    configured = command or settings.local_mcp_command
    cmd = sys.executable if configured in {"python", "python3"} else configured
    argv = args if args is not None else settings.local_args_list

    # Resolve relative script paths against the repository root.
    resolved_args: list[str] = []
    for arg in argv:
        path = Path(arg)
        if not path.is_absolute() and (REPO_ROOT / path).exists():
            resolved_args.append(str((REPO_ROOT / path).resolve()))
        else:
            resolved_args.append(arg)

    # STDIO children get a minimal env allow-list; merge extras explicitly.
    child_env = {**os.environ, **(env or {})}

    return StdioServerParameters(
        command=cmd,
        args=resolved_args,
        env=child_env,
        cwd=str(REPO_ROOT),
    )


@asynccontextmanager
async def connect_local_mcp(
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> AsyncIterator[ClientSession]:
    """
    Open a ClientSession to a local MCP server over STDIO.

    Usage::

        async with connect_local_mcp() as session:
            tools = await session.list_tools()
    """
    params = build_stdio_params(command=command, args=args, env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session
