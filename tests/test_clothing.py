"""Unit tests for the rule-based clothing engine."""

from clothes_recommend.domain.clothing import recommend_from_snapshot, recommend_outfit, temperature_band
from clothes_recommend.domain.models import LocationMatch, WeatherSnapshot


def test_temperature_band_boundaries() -> None:
    assert temperature_band(-0.1) == "freezing"
    assert temperature_band(0) == "cold"
    assert temperature_band(9.9) == "cold"
    assert temperature_band(10) == "cool"
    assert temperature_band(17.9) == "cool"
    assert temperature_band(18) == "mild"
    assert temperature_band(23.9) == "mild"
    assert temperature_band(24) == "warm"
    assert temperature_band(29.9) == "warm"
    assert temperature_band(30) == "hot"


def test_freezing_base_outfit() -> None:
    outfit = recommend_outfit(
        temperature_c=-5,
        weather_code=0,
        weather_label="Clear sky",
        location_label="Montreal",
    )
    assert outfit.temperature_band == "freezing"
    assert "Insulated winter coat" in outfit.outerwear
    assert "Cotton-only layers" in outfit.avoid
    assert any("wind" in note.lower() for note in outfit.notes)


def test_rain_modifier_adds_waterproof_gear() -> None:
    outfit = recommend_outfit(
        temperature_c=16,
        weather_code=61,
        weather_label="Slight rain",
        location_label="Seoul",
    )
    assert "Waterproof rain jacket" in outfit.outerwear
    assert "Compact umbrella" in outfit.accessories
    assert "Suede shoes" in outfit.avoid


def test_snow_modifier_prioritizes_traction() -> None:
    outfit = recommend_outfit(
        temperature_c=-2,
        weather_code=73,
        weather_label="Moderate snow fall",
        location_label="Oslo",
    )
    assert any("snow boots" in item.lower() for item in outfit.footwear)
    assert "Smooth-sole shoes" in outfit.avoid


def test_wind_and_humidity_notes() -> None:
    outfit = recommend_outfit(
        temperature_c=28,
        weather_code=0,
        weather_label="Clear sky",
        location_label="Singapore",
        wind_speed_kmh=35,
        relative_humidity_pct=85,
    )
    assert "Windbreaker or windproof shell" in outfit.outerwear
    assert any("humidity" in note.lower() for note in outfit.notes)
    assert any("wind" in note.lower() for note in outfit.notes)


def test_apparent_temperature_drives_band() -> None:
    outfit = recommend_outfit(
        temperature_c=12,
        weather_code=0,
        weather_label="Clear sky",
        location_label="Chicago",
        apparent_temperature_c=-3,
    )
    assert outfit.temperature_band == "freezing"


def test_recommend_from_snapshot() -> None:
    snapshot = WeatherSnapshot(
        location=LocationMatch(
            name="Tokyo",
            country="Japan",
            admin1="Tokyo",
            latitude=35.68,
            longitude=139.76,
            timezone="Asia/Tokyo",
        ),
        observed_at="2026-07-29T12:00",
        temperature_c=22.0,
        apparent_temperature_c=23.0,
        weather_code=2,
        weather_label="Partly cloudy",
        wind_speed_kmh=10.0,
        relative_humidity_pct=55,
    )
    outfit = recommend_from_snapshot(snapshot)
    assert outfit.temperature_band == "mild"
    assert "Tokyo" in outfit.location_label
    assert "Japan" in outfit.location_label
