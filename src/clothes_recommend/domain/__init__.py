"""Domain package exports."""

from clothes_recommend.domain.clothing import recommend_from_snapshot, recommend_outfit
from clothes_recommend.domain.models import OutfitRecommendation, WeatherSnapshot
from clothes_recommend.domain.weather import WeatherService, WeatherServiceError, fetch_weather

__all__ = [
    "OutfitRecommendation",
    "WeatherService",
    "WeatherServiceError",
    "WeatherSnapshot",
    "fetch_weather",
    "recommend_from_snapshot",
    "recommend_outfit",
]
