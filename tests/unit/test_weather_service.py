import httpx
import pytest

from assistant.backend.application.services.weather_service import WeatherService
from assistant.backend.shared.exceptions import (
    WeatherLocationNotFoundError,
    WeatherServiceError,
)


def build_service() -> WeatherService:
    return WeatherService(
        geocoding_url="https://geocoding-api.open-meteo.com/v1/search",
        forecast_url="https://api.open-meteo.com/v1/forecast",
        timeout_seconds=10.0,
    )


class StubResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("bad status", request=request, response=response)


def test_weather_service_returns_snapshot(monkeypatch) -> None:
    responses = iter(
        [
            StubResponse(
                {
                    "results": [
                        {
                            "name": "Delhi",
                            "country": "India",
                            "latitude": 28.61,
                            "longitude": 77.20,
                        }
                    ]
                }
            ),
            StubResponse({"current": {"temperature_2m": 34.2, "weather_code": 0}}),
        ]
    )

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: next(responses))

    service = build_service()
    snapshot = service.get_weather("Delhi")

    assert snapshot.location == "Delhi, India"
    assert snapshot.temperature_c == 34
    assert snapshot.condition == "Clear sky"


def test_weather_service_raises_not_found(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: StubResponse({"results": []}))

    service = build_service()

    with pytest.raises(WeatherLocationNotFoundError):
        service.get_weather("Atlantis")


def test_weather_service_raises_service_error_for_http_failures(monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise httpx.ConnectError("connection failed")

    monkeypatch.setattr(httpx, "get", fail)

    service = build_service()

    with pytest.raises(WeatherServiceError):
        service.get_weather("Delhi")
