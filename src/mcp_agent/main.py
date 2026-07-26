"""
CLI entry point for the MCP agent demos.

Examples
--------
Connect only to the local STDIO server::

    python -m mcp_agent.main local

Connect only to the remote Streamable HTTP server
(start ``servers/remote_http/server.py`` first)::

    python -m mcp_agent.main remote

Connect to both::

    python -m mcp_agent.main both
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow `python -m mcp_agent.main` from the repo root without installing.
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC.parent) not in sys.path:
    sys.path.insert(0, str(_SRC.parent))

from mcp_agent.agent.runner import demo_both, demo_local, demo_remote


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Demo agent that connects to local and/or remote MCP servers.",
    )
    parser.add_argument(
        "target",
        choices=("local", "remote", "both"),
        help="Which MCP server(s) to connect to",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.target == "local":
        asyncio.run(demo_local())
    elif args.target == "remote":
        asyncio.run(demo_remote())
    else:
        asyncio.run(demo_both())


if __name__ == "__main__":
    main()
