"""Clothes Recommend System orchestration over FastMCP."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Literal

from clothes_recommend.clients import (
    connect_inprocess_mcp,
    connect_local_mcp,
    connect_remote_mcp,
)
from clothes_recommend.clients.base import call_tool_data, list_tool_names
from clothes_recommend.config import get_settings

TransportName = Literal["inprocess", "stdio", "remote"]


def _print_recommendation(payload: dict[str, Any]) -> None:
    if not payload.get("ok", True):
        print(f"Error: {payload.get('error', 'unknown failure')}")
        return

    recommendation = payload.get("recommendation", payload)
    weather = payload.get("weather")

    if weather:
        loc = weather.get("location") or {}
        place = loc.get("name") or recommendation.get("location_label", "")
        print(
            f"Weather ({place}): {weather.get('weather_label')} | "
            f"{weather.get('temperature_c')}°C "
            f"(feels like {weather.get('apparent_temperature_c')}°C)"
        )

    print(recommendation.get("summary", ""))
    for section in ("base_layers", "outerwear", "bottoms", "footwear", "accessories"):
        items = recommendation.get(section) or []
        if items:
            print(f"  {section.replace('_', ' ').title()}: {', '.join(items)}")
    avoid = recommendation.get("avoid") or []
    if avoid:
        print(f"  Avoid: {', '.join(avoid)}")
    for note in recommendation.get("notes") or []:
        print(f"  Note: {note}")


def _client_for(transport: TransportName):
    if transport == "inprocess":
        return connect_inprocess_mcp()
    if transport == "stdio":
        return connect_local_mcp(keep_alive=True)
    return connect_remote_mcp()


def _label(transport: TransportName) -> str:
    return {
        "inprocess": "local FastMCP (in-process)",
        "stdio": "local MCP (STDIO keep-alive)",
        "remote": "remote MCP (Streamable HTTP)",
    }[transport]


async def recommend_via_client(transport: TransportName, location: str) -> None:
    """
    Run recommendation through one MCP surface.

    Uses ``recommend_clothes_for_location`` for a single round-trip instead of
    separate weather + clothing calls.
    """
    settings = get_settings()
    place = location or settings.default_location
    print(f"=== Clothes Recommend System · {_label(transport)} · {place} ===")

    started = time.perf_counter()
    async with _client_for(transport) as client:
        tools = await list_tool_names(client)
        print(f"Tools: {tools}")

        payload = await call_tool_data(
            client,
            "recommend_clothes_for_location",
            {"location": place},
        )

    elapsed_ms = (time.perf_counter() - started) * 1000
    print(f"Round-trip: {elapsed_ms:.0f} ms (single FastMCP tool call)")

    if not isinstance(payload, dict):
        print("Unexpected tool response.")
        return

    if payload.get("weather"):
        print("Weather payload:")
        print(json.dumps(payload["weather"], indent=2, ensure_ascii=False))

    print("Recommendation:")
    _print_recommendation(payload)


async def run_inprocess(location: str | None = None) -> None:
    await recommend_via_client(
        "inprocess",
        location or get_settings().default_location,
    )


async def run_stdio(location: str | None = None) -> None:
    await recommend_via_client(
        "stdio",
        location or get_settings().default_location,
    )


async def run_local(location: str | None = None) -> None:
    """Default local path: in-process FastMCP (fastest)."""
    await run_inprocess(location)


async def run_remote(location: str | None = None) -> None:
    await recommend_via_client(
        "remote",
        location or get_settings().default_location,
    )


async def run_both(location: str | None = None) -> None:
    """Run in-process and remote recommendations concurrently."""
    place = location or get_settings().default_location
    started = time.perf_counter()
    await asyncio.gather(
        recommend_via_client("inprocess", place),
        recommend_via_client("remote", place),
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    print(f"\nConcurrent local+remote wall time: {elapsed_ms:.0f} ms")
