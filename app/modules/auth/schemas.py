from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.common.enums import UserRole


class RegisterUserRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "StrongPass1!",  # nosec B105
                "full_name": "Example User",
            }
        },
    )

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if value.lower() == value:
            raise ValueError("Password must include an uppercase character.")
        if value.upper() == value:
            raise ValueError("Password must include a lowercase character.")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must include a digit.")
        if not any(not char.isalnum() for char in value):
            raise ValueError("Password must include a special character.")
        return value


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "refresh_token": "demo-refresh-token",  # nosec B105
            }
        },
    )

    refresh_token: str = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "user@example.com",
                "full_name": "Example User",
                "role": "user",
                "is_active": True,
                "is_verified": False,
                "created_at": "2026-04-09T12:00:00Z",
                "updated_at": "2026-04-09T12:00:00Z",
            }
        },
    )

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "access_token": "demo-access-token",  # nosec B105
                "refresh_token": "demo-refresh-token",  # nosec B105
                "token_type": "bearer",  # nosec B105
                "access_token_expires_at": "2026-04-09T12:30:00Z",  # nosec B105
                "refresh_token_expires_at": "2026-04-16T12:00:00Z",  # nosec B105
            }
        },
    )

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # nosec B105
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
