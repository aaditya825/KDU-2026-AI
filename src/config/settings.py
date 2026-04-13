"""Configuration and settings for the Stock Trading Agent"""
import os
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Google Gemini API
    google_api_key: str = ""

    # LangSmith Configuration
    langsmith_api_key: str = ""
    langsmith_project: str = "stock-trading-agent"
    langchain_tracing_v2: bool = True
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # App Configuration
    database_path: str = "data/checkpoints.db"
    debug: bool = False
    log_level: str = "INFO"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        """Gracefully coerce DEBUG values instead of failing on non-boolean strings."""
        if isinstance(value, bool):
            return value

        if value is None:
            return False

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "t", "yes", "y", "on", "debug"}:
                return True
            if normalized in {"0", "false", "f", "no", "n", "off", "release", "prod", "production"}:
                return False

        return False

    def setup_langsmith_env(self):
        """Configure LangSmith environment variables"""
        if self.langchain_tracing_v2:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = self.langsmith_project
            os.environ["LANGCHAIN_API_KEY"] = self.langsmith_api_key
            os.environ["LANGCHAIN_ENDPOINT"] = self.langchain_endpoint


# Global settings instance
settings = Settings()

# Initialize LangSmith environment
if settings.langsmith_api_key:
    settings.setup_langsmith_env()
