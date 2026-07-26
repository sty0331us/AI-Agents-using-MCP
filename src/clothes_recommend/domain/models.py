"""Domain models for weather lookup and clothing recommendations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LocationMatch(BaseModel):
    """Resolved place from geocoding."""

    name: str
    country: str | None = None
    admin1: str | None = None
    latitude: float
    longitude: float
    timezone: str | None = None


class WeatherSnapshot(BaseModel):
    """Current conditions for a resolved location."""

    location: LocationMatch
    observed_at: str
    temperature_c: float
    apparent_temperature_c: float | None = None
    relative_humidity_pct: int | None = None
    precipitation_mm: float | None = None
    weather_code: int
    weather_label: str
    wind_speed_kmh: float | None = None
    is_day: bool | None = None
    source: str = "Open-Meteo"


TemperatureBand = Literal[
    "freezing",
    "cold",
    "cool",
    "mild",
    "warm",
    "hot",
]


class OutfitRecommendation(BaseModel):
    """Structured clothing recommendation derived from weather."""

    location_label: str
    temperature_c: float
    apparent_temperature_c: float | None = None
    weather_label: str
    temperature_band: TemperatureBand
    summary: str
    base_layers: list[str] = Field(default_factory=list)
    outerwear: list[str] = Field(default_factory=list)
    bottoms: list[str] = Field(default_factory=list)
    footwear: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
