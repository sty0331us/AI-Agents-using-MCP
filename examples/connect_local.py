"""
Clothes Recommend · local MCP runtime (STDIO).

    PYTHONPATH=src python examples/connect_local.py --location "Seoul"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from clothes_recommend.agent.runner import run_local
from clothes_recommend.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clothes Recommend · local MCP (STDIO)",
    )
    parser.add_argument(
        "--location",
        "-l",
        default=get_settings().default_location,
        help="City or place name",
    )
    args = parser.parse_args()
    asyncio.run(run_local(args.location))


if __name__ == "__main__":
    main()
