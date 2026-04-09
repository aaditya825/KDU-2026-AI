from functools import lru_cache
from typing import Literal, cast

from pydantic import Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_name: str = "FastAPI Production Template"
    project_description: str = "Reusable production-ready FastAPI starter template"
    version: str = "0.1.0"
    environment: Literal["local", "development", "test", "staging", "production"] = "development"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    api_v1_prefix: str = "/api/v1"
    expose_docs: bool = True

    log_level: str = "INFO"
    log_json: bool = False

    backend_cors_origins: list[str] = Field(default_factory=list)
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )
    cors_allow_headers: list[str] = Field(
        default_factory=lambda: ["Authorization", "Content-Type", "X-Request-ID"]
    )

    secret_key: SecretStr = Field(
        default=SecretStr("change-this-to-a-strong-random-secret-with-at-least-32-characters")
    )
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    rate_limit_auth: str = "5/minute"

    database_url: PostgresDsn = Field(
        default=cast(
            PostgresDsn,
            "postgresql+asyncpg://postgres:postgres@localhost:5432/fastapi_app",
        )
    )
    test_database_url: PostgresDsn = Field(
        default=cast(
            PostgresDsn,
            "postgresql+asyncpg://postgres:postgres@localhost:5433/fastapi_app_test",
        )
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True

    @field_validator(
        "backend_cors_origins",
        "cors_allow_methods",
        "cors_allow_headers",
        mode="before",
    )
    @classmethod
    def parse_csv_list(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def docs_url(self) -> str | None:
        return "/docs" if self.expose_docs else None

    @property
    def redoc_url(self) -> str | None:
        return "/redoc" if self.expose_docs else None

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @field_validator("secret_key")
    @classmethod
    def validate_secret_length(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
