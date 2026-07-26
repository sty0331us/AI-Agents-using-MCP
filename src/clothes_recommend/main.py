"""
Clothes Recommend System — CLI entry point.

Examples
--------
Local FastMCP server (STDIO)::

    python -m clothes_recommend.main local --location "Seoul"

Remote FastMCP server (Streamable HTTP; start the remote server first)::

    python -m clothes_recommend.main remote --location "Tokyo"

Both servers concurrently::

    python -m clothes_recommend.main both --location "London"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC.parent) not in sys.path:
    sys.path.insert(0, str(_SRC.parent))

from clothes_recommend import __app_name__
from clothes_recommend.agent.runner import run_both, run_local, run_remote
from clothes_recommend.config import get_settings


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        prog="clothes-recommend",
        description=(
            f"{__app_name__}: live weather + outfit recommendations via FastMCP "
            "(local STDIO or remote Streamable HTTP)."
        ),
    )
    parser.add_argument(
        "target",
        choices=("local", "remote", "both"),
        help="MCP server: local (STDIO), remote (Streamable HTTP), or both",
    )
    parser.add_argument(
        "--location",
        "-l",
        default=settings.default_location,
        help=f"City or place name (default: {settings.default_location})",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.target == "local":
        asyncio.run(run_local(args.location))
    elif args.target == "remote":
        asyncio.run(run_remote(args.location))
    else:
        asyncio.run(run_both(args.location))


if __name__ == "__main__":
    main()
