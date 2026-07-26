"""Register Clothes Recommend MCP tools on a FastMCP server instance."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from clothes_recommend.domain.clothing import recommend_from_snapshot, recommend_outfit
from clothes_recommend.domain.weather import WeatherServiceError, fetch_weather
from clothes_recommend.domain.wmo import weather_label


def register_clothes_tools(mcp: FastMCP) -> FastMCP:
    """Attach weather and clothing tools to the given FastMCP server."""

    @mcp.tool
    async def get_location_weather(location: str) -> dict[str, Any]:
        """
        Look up today's current weather for a city or place name.

        Resolves the location via geocoding, then returns live temperature,
        apparent temperature, humidity, precipitation, wind, and weather
        conditions. Prefer recommend_clothes_for_location when you only need
        an outfit (one MCP round-trip instead of two).
        """
        try:
            snapshot = await fetch_weather(location)
        except WeatherServiceError as exc:
            return {"ok": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001 — surface provider failures to the client
            return {"ok": False, "error": f"Weather lookup failed: {exc}"}

        return {
            "ok": True,
            "location": {
                "name": snapshot.location.name,
                "admin1": snapshot.location.admin1,
                "country": snapshot.location.country,
                "latitude": snapshot.location.latitude,
                "longitude": snapshot.location.longitude,
                "timezone": snapshot.location.timezone,
            },
            "observed_at": snapshot.observed_at,
            "temperature_c": snapshot.temperature_c,
            "apparent_temperature_c": snapshot.apparent_temperature_c,
            "relative_humidity_pct": snapshot.relative_humidity_pct,
            "precipitation_mm": snapshot.precipitation_mm,
            "weather_code": snapshot.weather_code,
            "weather_label": snapshot.weather_label,
            "wind_speed_kmh": snapshot.wind_speed_kmh,
            "is_day": snapshot.is_day,
            "source": snapshot.source,
        }

    @mcp.tool
    def recommend_clothes(
        temperature_c: float,
        weather_code: int,
        location_label: str = "selected location",
        apparent_temperature_c: float | None = None,
        wind_speed_kmh: float | None = None,
        relative_humidity_pct: int | None = None,
    ) -> dict[str, Any]:
        """
        Recommend an outfit from temperature and weather conditions.

        Pass temperature_c and a WMO weather_code (from get_location_weather).
        Optional apparent_temperature_c, wind_speed_kmh, and humidity refine
        the recommendation. Returns base layers, outerwear, bottoms, footwear,
        accessories, items to avoid, and brief notes.
        """
        outfit = recommend_outfit(
            temperature_c=temperature_c,
            weather_code=weather_code,
            weather_label=weather_label(weather_code),
            location_label=location_label,
            apparent_temperature_c=apparent_temperature_c,
            wind_speed_kmh=wind_speed_kmh,
            relative_humidity_pct=relative_humidity_pct,
        )
        return {"ok": True, **outfit.model_dump()}

    @mcp.tool
    async def recommend_clothes_for_location(location: str) -> dict[str, Any]:
        """
        Fast path: fetch today's weather and recommend clothes in one call.

        Prefer this tool to avoid an extra MCP round-trip when the caller only
        has a place name.
        """
        try:
            snapshot = await fetch_weather(location)
        except WeatherServiceError as exc:
            return {"ok": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"Weather lookup failed: {exc}"}

        outfit = recommend_from_snapshot(snapshot)
        return {
            "ok": True,
            "weather": {
                "observed_at": snapshot.observed_at,
                "temperature_c": snapshot.temperature_c,
                "apparent_temperature_c": snapshot.apparent_temperature_c,
                "weather_code": snapshot.weather_code,
                "weather_label": snapshot.weather_label,
                "wind_speed_kmh": snapshot.wind_speed_kmh,
                "relative_humidity_pct": snapshot.relative_humidity_pct,
                "precipitation_mm": snapshot.precipitation_mm,
                "is_day": snapshot.is_day,
                "location": {
                    "name": snapshot.location.name,
                    "admin1": snapshot.location.admin1,
                    "country": snapshot.location.country,
                    "latitude": snapshot.location.latitude,
                    "longitude": snapshot.location.longitude,
                    "timezone": snapshot.location.timezone,
                },
                "source": snapshot.source,
            },
            "recommendation": outfit.model_dump(),
        }

    return mcp
