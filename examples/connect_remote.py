"""
Fetch weather and recommend clothes via the remote MCP server.

Start the server first::

    python servers/remote_http/server.py

Then::

    PYTHONPATH=src python examples/connect_remote.py --location "Tokyo"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from clothes_recommend.agent.runner import run_remote
from clothes_recommend.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Clothes Recommend · remote MCP")
    parser.add_argument(
        "--location",
        "-l",
        default=get_settings().default_location,
        help="City or place name",
    )
    args = parser.parse_args()
    asyncio.run(run_remote(args.location))


if __name__ == "__main__":
    main()
