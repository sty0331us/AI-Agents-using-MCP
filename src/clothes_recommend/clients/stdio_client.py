"""Local FastMCP client using STDIO transport."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from clothes_recommend.config import REPO_ROOT, get_settings


def build_stdio_transport(
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> StdioTransport:
    """Build a FastMCP StdioTransport for the local MCP server."""
    settings = get_settings()
    configured = command or settings.local_mcp_command
    cmd = sys.executable if configured in {"python", "python3"} else configured
    argv = args if args is not None else settings.local_args_list

    resolved_args: list[str] = []
    for arg in argv:
        path = Path(arg)
        if not path.is_absolute() and (REPO_ROOT / path).exists():
            resolved_args.append(str((REPO_ROOT / path).resolve()))
        else:
            resolved_args.append(arg)

    return StdioTransport(
        command=cmd,
        args=resolved_args,
        env={**os.environ, **(env or {})},
        cwd=str(REPO_ROOT),
    )


def connect_local_mcp(
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> Client:
    """
    Return a FastMCP Client for the local Clothes Recommend STDIO server.

    The client launches ``servers/local_stdio/server.py`` as a subprocess and
    speaks MCP over stdin/stdout.
    """
    return Client(build_stdio_transport(command=command, args=args, env=env))
