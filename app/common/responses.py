from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorBody(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "code": "validation_error",
                "message": "Request validation failed.",
                "details": [
                    {
                        "type": "string_too_short",
                        "loc": ["body", "full_name"],
                        "msg": "String should have at least 1 character",
                    }
                ],
                "request_id": "f4b2d667-1a77-49a4-95f5-512c7d3d8cfd",
            }
        },
    )

    code: str
    message: str
    details: Any | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "details": [
                        {
                            "type": "string_too_short",
                            "loc": ["body", "full_name"],
                            "msg": "String should have at least 1 character",
                        }
                    ],
                    "request_id": "f4b2d667-1a77-49a4-95f5-512c7d3d8cfd",
                }
            }
        },
    )

    error: ErrorBody


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "status": "ok",
                "service": "FastAPI Production Template",
                "environment": "development",
                "timestamp": "2026-04-09T12:00:00Z",
            }
        },
    )

    status: str
    service: str
    environment: str
    timestamp: datetime


class VersionResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "service": "FastAPI Production Template",
                "version": "0.1.0",
                "environment": "development",
            }
        },
    )

    service: str
    version: str
    environment: str
