"""Rule-based clothing recommendation engine."""

from __future__ import annotations

from clothes_recommend.domain.models import (
    OutfitRecommendation,
    TemperatureBand,
    WeatherSnapshot,
)
from clothes_recommend.domain.wmo import is_foggy, is_rain, is_snow, is_stormy


def temperature_band(celsius: float) -> TemperatureBand:
    if celsius < 0:
        return "freezing"
    if celsius < 10:
        return "cold"
    if celsius < 18:
        return "cool"
    if celsius < 24:
        return "mild"
    if celsius < 30:
        return "warm"
    return "hot"


def recommend_outfit(
    *,
    temperature_c: float,
    weather_code: int,
    weather_label: str,
    location_label: str,
    apparent_temperature_c: float | None = None,
    wind_speed_kmh: float | None = None,
    relative_humidity_pct: int | None = None,
) -> OutfitRecommendation:
    """
    Build an outfit recommendation from temperature and WMO weather code.

    Uses apparent temperature when available (wind chill / heat index),
    then applies precipitation, wind, and humidity modifiers.
    """
    effective = (
        apparent_temperature_c if apparent_temperature_c is not None else temperature_c
    )
    band = temperature_band(effective)

    base_layers: list[str] = []
    outerwear: list[str] = []
    bottoms: list[str] = []
    footwear: list[str] = []
    accessories: list[str] = []
    avoid: list[str] = []
    notes: list[str] = []

    if band == "freezing":
        base_layers = ["Thermal base layer", "Heavy sweater or fleece"]
        outerwear = ["Insulated winter coat", "Windproof shell"]
        bottoms = ["Insulated pants or thermal-lined jeans"]
        footwear = ["Insulated waterproof boots"]
        accessories = ["Knit beanie", "Insulated gloves", "Wool scarf"]
        avoid = ["Cotton-only layers", "Open-toe shoes"]
        notes.append("Prioritize wind protection and extremity coverage.")
    elif band == "cold":
        base_layers = ["Long-sleeve shirt", "Sweater or hoodie"]
        outerwear = ["Winter coat or heavy parka"]
        bottoms = ["Jeans or thick trousers"]
        footwear = ["Closed boots or sturdy sneakers"]
        accessories = ["Light gloves", "Scarf (optional)"]
        avoid = ["Shorts", "Sleeveless tops"]
    elif band == "cool":
        base_layers = ["Long-sleeve shirt or light sweater"]
        outerwear = ["Light jacket or denim jacket"]
        bottoms = ["Jeans or chinos"]
        footwear = ["Sneakers or loafers"]
        accessories = ["Light scarf (optional)"]
        avoid = ["Heavy down coats (overheating risk)"]
    elif band == "mild":
        base_layers = ["T-shirt or breathable button-up"]
        outerwear = ["Optional light cardigan or overshirt"]
        bottoms = ["Chinos, jeans, or casual trousers"]
        footwear = ["Sneakers or casual shoes"]
        accessories = []
        avoid = ["Heavy coats"]
    elif band == "warm":
        base_layers = ["Breathable T-shirt or short-sleeve shirt"]
        outerwear = []
        bottoms = ["Light trousers or shorts"]
        footwear = ["Breathable sneakers or sandals"]
        accessories = ["Sunglasses", "Cap or sun hat"]
        avoid = ["Thick fabrics", "Multiple insulating layers"]
        notes.append("Prefer moisture-wicking materials.")
    else:  # hot
        base_layers = ["Lightweight, light-colored shirt"]
        outerwear = []
        bottoms = ["Shorts or very light trousers"]
        footwear = ["Breathable open footwear"]
        accessories = ["Wide-brim hat", "Sunglasses", "Reusable water bottle"]
        avoid = ["Dark heavy fabrics", "Non-breathable synthetics"]
        notes.append("Minimize sun exposure during peak heat.")

    if is_rain(weather_code):
        outerwear = _unique([*outerwear, "Waterproof rain jacket"])
        footwear = _unique([*footwear, "Water-resistant shoes"])
        accessories = _unique([*accessories, "Compact umbrella"])
        avoid = _unique([*avoid, "Suede shoes", "Non-waterproof bags"])
        notes.append("Expect wet conditions — keep an outer shell accessible.")

    if is_snow(weather_code):
        outerwear = _unique([*outerwear, "Waterproof insulated coat"])
        footwear = _unique(["Waterproof snow boots with tread"])
        accessories = _unique([*accessories, "Insulated gloves", "Warm hat"])
        avoid = _unique([*avoid, "Smooth-sole shoes"])
        notes.append("Snow and ice — prioritize traction and insulation.")

    if is_stormy(weather_code):
        accessories = _unique([*accessories, "Avoid metal umbrellas outdoors"])
        notes.append("Thunderstorm risk — reduce outdoor exposure if possible.")

    if is_foggy(weather_code):
        accessories = _unique([*accessories, "High-visibility layer if commuting"])
        notes.append("Low visibility — choose brighter outer layers for commuting.")

    if wind_speed_kmh is not None and wind_speed_kmh >= 30:
        outerwear = _unique([*outerwear, "Windbreaker or windproof shell"])
        notes.append(f"Elevated wind ({wind_speed_kmh:.0f} km/h) — seal heat with a shell.")

    if relative_humidity_pct is not None and relative_humidity_pct >= 80 and band in {
        "warm",
        "hot",
    }:
        notes.append("High humidity — choose loose, breathable fabrics.")

    summary = (
        f"For {location_label}: {weather_label.lower()} at {temperature_c:.1f}°C "
        f"(feels like {effective:.1f}°C) — dress for a {band} day."
    )

    return OutfitRecommendation(
        location_label=location_label,
        temperature_c=temperature_c,
        apparent_temperature_c=apparent_temperature_c,
        weather_label=weather_label,
        temperature_band=band,
        summary=summary,
        base_layers=base_layers,
        outerwear=outerwear,
        bottoms=bottoms,
        footwear=footwear,
        accessories=accessories,
        avoid=avoid,
        notes=notes,
    )


def recommend_from_snapshot(snapshot: WeatherSnapshot) -> OutfitRecommendation:
    location = snapshot.location
    parts = [location.name]
    if location.admin1:
        parts.append(location.admin1)
    if location.country:
        parts.append(location.country)
    label = ", ".join(parts)
    return recommend_outfit(
        temperature_c=snapshot.temperature_c,
        weather_code=snapshot.weather_code,
        weather_label=snapshot.weather_label,
        location_label=label,
        apparent_temperature_c=snapshot.apparent_temperature_c,
        wind_speed_kmh=snapshot.wind_speed_kmh,
        relative_humidity_pct=snapshot.relative_humidity_pct,
    )


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
