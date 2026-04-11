from dataclasses import dataclass

import httpx

from assistant.backend.shared.exceptions import (
    WeatherLocationNotFoundError,
    WeatherServiceError,
)


@dataclass(slots=True)
class WeatherSnapshot:
    """Typed weather data returned by the weather service."""

    location: str
    temperature_c: int
    condition: str


class WeatherService:
    """Real weather backend using Open-Meteo geocoding and forecast APIs."""

    def __init__(
        self,
        *,
        geocoding_url: str,
        forecast_url: str,
        timeout_seconds: float,
    ) -> None:
        self._geocoding_url = geocoding_url
        self._forecast_url = forecast_url
        self._timeout = timeout_seconds

    def get_weather(self, location: str) -> WeatherSnapshot:
        resolved_location = location.strip()
        if not resolved_location:
            raise WeatherLocationNotFoundError("Location is required to fetch weather.")

        latitude, longitude, display_name = self._resolve_location(resolved_location)
        current_weather = self._fetch_current_weather(latitude=latitude, longitude=longitude)

        return WeatherSnapshot(
            location=display_name,
            temperature_c=round(float(current_weather["temperature_2m"])),
            condition=self._map_weather_code(int(current_weather["weather_code"])),
        )

    def _resolve_location(self, location: str) -> tuple[float, float, str]:
        try:
            response = httpx.get(
                self._geocoding_url,
                params={
                    "name": location,
                    "count": 1,
                    "language": "en",
                    "format": "json",
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WeatherServiceError(
                "The weather geocoding service is currently unavailable."
            ) from exc

        payload = response.json()
        results = payload.get("results") or []
        if not results:
            raise WeatherLocationNotFoundError(
                f"Could not find a weather location match for '{location}'."
            )

        top_match = results[0]
        name = top_match["name"]
        country = top_match.get("country")
        display_name = f"{name}, {country}" if country and country.lower() not in name.lower() else name

        return (
            float(top_match["latitude"]),
            float(top_match["longitude"]),
            display_name,
        )

    def _fetch_current_weather(self, *, latitude: float, longitude: float) -> dict:
        try:
            response = httpx.get(
                self._forecast_url,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "temperature_2m,weather_code",
                    "temperature_unit": "celsius",
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WeatherServiceError(
                "The weather forecast service is currently unavailable."
            ) from exc

        payload = response.json()
        current = payload.get("current")
        if not current:
            raise WeatherServiceError("The weather forecast service returned no current weather data.")

        return current

    def _map_weather_code(self, code: int) -> str:
        weather_code_map = {
            0: "Clear sky",
            1: "Mostly clear",
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
            71: "Slight snowfall",
            73: "Moderate snowfall",
            75: "Heavy snowfall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with light hail",
            99: "Thunderstorm with heavy hail",
        }
        return weather_code_map.get(code, "Unknown conditions")
