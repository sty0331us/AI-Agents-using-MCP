"""Clothes Recommend System orchestration over FastMCP."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Literal

from clothes_recommend.clients import connect_local_mcp, connect_remote_mcp
from clothes_recommend.clients.base import call_tool_data, list_tool_names
from clothes_recommend.config import get_settings

TransportName = Literal["local", "remote"]


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
    if transport == "local":
        return connect_local_mcp()
    return connect_remote_mcp()


def _label(transport: TransportName) -> str:
    if transport == "local":
        return "local MCP (STDIO)"
    return "remote MCP (Streamable HTTP)"


async def recommend_via_client(
    transport: TransportName,
    location: str,
    *,
    as_json: bool = False,
) -> dict[str, Any] | None:
    """Run recommendation through the local STDIO or remote HTTP MCP server."""
    settings = get_settings()
    place = location or settings.default_location

    if not as_json:
        print(f"=== Clothes Recommend System · {_label(transport)} · {place} ===")

    started = time.perf_counter()
    async with _client_for(transport) as client:
        tools = await list_tool_names(client)
        if not as_json:
            print(f"Tools: {tools}")

        payload = await call_tool_data(
            client,
            "recommend_clothes_for_location",
            {"location": place},
        )

    elapsed_ms = (time.perf_counter() - started) * 1000
    envelope = {
        "transport": transport,
        "location": place,
        "elapsed_ms": round(elapsed_ms),
        "tools": tools,
        "result": payload,
    }

    if as_json:
        return envelope

    print(f"Elapsed: {elapsed_ms:.0f} ms")

    if not isinstance(payload, dict):
        print("Unexpected tool response.")
        return None

    if payload.get("weather"):
        print("Weather payload:")
        print(json.dumps(payload["weather"], indent=2, ensure_ascii=False))

    print("Recommendation:")
    _print_recommendation(payload)
    return None


async def run_local(location: str | None = None, *, as_json: bool = False) -> None:
    """Connect to the local FastMCP server over STDIO."""
    envelope = await recommend_via_client(
        "local",
        location or get_settings().default_location,
        as_json=as_json,
    )
    if as_json and envelope is not None:
        print(json.dumps(envelope, indent=2, ensure_ascii=False))


async def run_remote(location: str | None = None, *, as_json: bool = False) -> None:
    """Connect to the remote FastMCP server over Streamable HTTP."""
    envelope = await recommend_via_client(
        "remote",
        location or get_settings().default_location,
        as_json=as_json,
    )
    if as_json and envelope is not None:
        print(json.dumps(envelope, indent=2, ensure_ascii=False))


async def run_both(location: str | None = None, *, as_json: bool = False) -> None:
    """Query local STDIO and remote HTTP servers concurrently."""
    place = location or get_settings().default_location
    started = time.perf_counter()
    envelopes = await asyncio.gather(
        recommend_via_client("local", place, as_json=as_json),
        recommend_via_client("remote", place, as_json=as_json),
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    if as_json:
        print(
            json.dumps(
                {
                    "mode": "both",
                    "location": place,
                    "wall_elapsed_ms": round(elapsed_ms),
                    "results": list(envelopes),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    print(f"\nConcurrent local+remote wall time: {elapsed_ms:.0f} ms")
