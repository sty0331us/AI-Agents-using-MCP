"""Factory for Clothes Recommend FastMCP servers."""

from __future__ import annotations

from fastmcp import FastMCP

from clothes_recommend.mcp_tools import register_clothes_tools


def create_clothes_mcp(name: str = "clothes-recommend") -> FastMCP:
    """
    Build a FastMCP server with weather + clothing tools.

    Used by the local STDIO and remote HTTP FastMCP servers so both share
    one tool registration path.
    """
    mcp = FastMCP(
        name=name,
        instructions=(
            "Clothes Recommend System. Prefer recommend_clothes_for_location for "
            "a single round-trip (weather + outfit). Use get_location_weather and "
            "recommend_clothes when the caller already has partial weather data."
        ),
    )
    register_clothes_tools(mcp)
    return mcp
