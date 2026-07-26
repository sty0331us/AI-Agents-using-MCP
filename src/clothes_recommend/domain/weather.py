"""Open-Meteo weather client with connection reuse and short-lived cache."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from clothes_recommend.domain.models import LocationMatch, WeatherSnapshot
from clothes_recommend.domain.wmo import weather_label

logger = logging.getLogger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

DEFAULT_TIMEOUT = httpx.Timeout(5.0, connect=3.0, read=10.0)
# Weather changes slowly enough that a short TTL cuts repeat geocode+forecast
# round-trips during agent retries and multi-tool flows.
DEFAULT_CACHE_TTL_SECONDS = 120.0

_shared_http: httpx.AsyncClient | None = None
_shared_http_lock = asyncio.Lock()


@dataclass
class _CacheEntry:
    snapshot: WeatherSnapshot
    expires_at: float


class WeatherServiceError(Exception):
    """Raised when location resolution or weather fetch fails."""


async def get_shared_http_client() -> httpx.AsyncClient:
    """Process-wide httpx client — connection pooling across tool calls."""
    global _shared_http
    if _shared_http is not None and not _shared_http.is_closed:
        return _shared_http
    async with _shared_http_lock:
        if _shared_http is None or _shared_http.is_closed:
            _shared_http = httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "ClothesRecommendSystem/1.0"},
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                    keepalive_expiry=30.0,
                ),
            )
        return _shared_http


class WeatherService:
    """Fetches live weather for a place name via Open-Meteo."""

    def __init__(
        self,
        *,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        client: httpx.AsyncClient | None = None,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        self._timeout = timeout
        self._client = client
        self._owns_client = client is None
        self._cache_ttl = cache_ttl_seconds
        self._cache: dict[str, _CacheEntry] = {}

    async def __aenter__(self) -> WeatherService:
        if self._client is None:
            self._client = await get_shared_http_client()
            self._owns_client = False
        return self

    async def __aexit__(self, *exc: object) -> None:
        # Shared process client is kept open for pooling; only close if we own one.
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("WeatherService must be used as an async context manager")
        return self._client

    def _cache_get(self, key: str) -> WeatherSnapshot | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.monotonic() >= entry.expires_at:
            self._cache.pop(key, None)
            return None
        return entry.snapshot

    def _cache_set(self, key: str, snapshot: WeatherSnapshot) -> None:
        if self._cache_ttl <= 0:
            return
        self._cache[key] = _CacheEntry(
            snapshot=snapshot,
            expires_at=time.monotonic() + self._cache_ttl,
        )

    async def resolve_location(self, query: str) -> LocationMatch:
        q = query.strip()
        if not q:
            raise WeatherServiceError("Location query must not be empty.")

        response = await self.client.get(
            GEOCODING_URL,
            params={"name": q, "count": 1, "language": "en", "format": "json"},
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        if not results:
            raise WeatherServiceError(f"No location found for {query!r}.")

        hit = results[0]
        return LocationMatch(
            name=hit["name"],
            country=hit.get("country"),
            admin1=hit.get("admin1"),
            latitude=float(hit["latitude"]),
            longitude=float(hit["longitude"]),
            timezone=hit.get("timezone"),
        )

    async def get_current_weather(self, location_query: str) -> WeatherSnapshot:
        cache_key = location_query.strip().casefold()
        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.debug("weather.cache_hit query=%s", location_query)
            return cached

        location = await self.resolve_location(location_query)
        response = await self.client.get(
            FORECAST_URL,
            params={
                "latitude": location.latitude,
                "longitude": location.longitude,
                "current": ",".join(
                    [
                        "temperature_2m",
                        "apparent_temperature",
                        "relative_humidity_2m",
                        "precipitation",
                        "weather_code",
                        "wind_speed_10m",
                        "is_day",
                    ]
                ),
                "timezone": "auto",
                "wind_speed_unit": "kmh",
            },
        )
        response.raise_for_status()
        payload = response.json()
        current = payload.get("current")
        if not current:
            raise WeatherServiceError("Weather provider returned no current conditions.")

        code = int(current["weather_code"])
        snapshot = WeatherSnapshot(
            location=location,
            observed_at=str(current.get("time", "")),
            temperature_c=float(current["temperature_2m"]),
            apparent_temperature_c=(
                float(current["apparent_temperature"])
                if current.get("apparent_temperature") is not None
                else None
            ),
            relative_humidity_pct=(
                int(current["relative_humidity_2m"])
                if current.get("relative_humidity_2m") is not None
                else None
            ),
            precipitation_mm=(
                float(current["precipitation"])
                if current.get("precipitation") is not None
                else None
            ),
            weather_code=code,
            weather_label=weather_label(code),
            wind_speed_kmh=(
                float(current["wind_speed_10m"])
                if current.get("wind_speed_10m") is not None
                else None
            ),
            is_day=bool(current["is_day"]) if current.get("is_day") is not None else None,
        )
        self._cache_set(cache_key, snapshot)
        logger.info(
            "weather.fetched location=%s temp_c=%.1f code=%s",
            _location_label(location),
            snapshot.temperature_c,
            snapshot.weather_code,
        )
        return snapshot


# Module-level service so tool calls in the same process share cache + HTTP pool.
_process_weather_service: WeatherService | None = None


def get_process_weather_service() -> WeatherService:
    global _process_weather_service
    if _process_weather_service is None:
        _process_weather_service = WeatherService()
    return _process_weather_service


def _location_label(location: LocationMatch) -> str:
    parts = [location.name]
    if location.admin1:
        parts.append(location.admin1)
    if location.country:
        parts.append(location.country)
    return ", ".join(parts)


async def fetch_weather(location_query: str) -> WeatherSnapshot:
    service = get_process_weather_service()
    async with service:
        return await service.get_current_weather(location_query)
