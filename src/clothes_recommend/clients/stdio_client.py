"""Local FastMCP client (STDIO transport) with session keep-alive."""

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
    *,
    keep_alive: bool = True,
) -> StdioTransport:
    """
    Build a STDIO transport.

    ``keep_alive=True`` (default) reuses the subprocess across client contexts,
    which is significantly faster for repeated calls.
    """
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
        keep_alive=keep_alive,
    )


def connect_local_mcp(
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    *,
    keep_alive: bool = True,
) -> Client:
    """Return a FastMCP Client for the local Clothes Recommend STDIO server."""
    return Client(
        build_stdio_transport(
            command=command,
            args=args,
            env=env,
            keep_alive=keep_alive,
        )
    )
