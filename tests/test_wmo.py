"""Unit tests for WMO weather code helpers."""

from clothes_recommend.domain.wmo import (
    is_foggy,
    is_precipitating,
    is_rain,
    is_snow,
    is_stormy,
    weather_label,
)


def test_weather_label_known_and_unknown() -> None:
    assert weather_label(0) == "Clear sky"
    assert weather_label(61) == "Slight rain"
    assert "999" in weather_label(999)


def test_precipitation_categories() -> None:
    assert is_rain(61)
    assert is_precipitating(61)
    assert not is_snow(61)

    assert is_snow(71)
    assert is_precipitating(71)
    assert not is_rain(71)

    assert not is_precipitating(0)
    assert not is_rain(0)
    assert not is_snow(0)


def test_storm_and_fog() -> None:
    assert is_stormy(95)
    assert is_stormy(99)
    assert not is_stormy(61)

    assert is_foggy(45)
    assert is_foggy(48)
    assert not is_foggy(0)
