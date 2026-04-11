from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = REPO_ROOT / ".env"


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables."""

    gemini_api_key: str | None = None
    assistant_model: str = "gemini-2.5-flash"
    assistant_max_image_bytes: int = 5 * 1024 * 1024
    weather_geocoding_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    weather_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_timeout_seconds: float = 10.0
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    backend_base_url: str = "http://127.0.0.1:8000"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
