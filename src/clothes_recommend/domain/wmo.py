"""WMO weather interpretation codes used by Open-Meteo."""

from __future__ import annotations

WMO_WEATHER_LABELS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def weather_label(code: int) -> str:
    return WMO_WEATHER_LABELS.get(code, f"Unknown conditions (code {code})")


def is_precipitating(code: int) -> bool:
    return code in {
        51, 53, 55, 56, 57,
        61, 63, 65, 66, 67,
        71, 73, 75, 77,
        80, 81, 82, 85, 86,
        95, 96, 99,
    }


def is_snow(code: int) -> bool:
    return code in {71, 73, 75, 77, 85, 86}


def is_rain(code: int) -> bool:
    return is_precipitating(code) and not is_snow(code)


def is_stormy(code: int) -> bool:
    return code in {95, 96, 99}


def is_foggy(code: int) -> bool:
    return code in {45, 48}
