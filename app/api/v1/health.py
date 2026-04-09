from datetime import UTC, datetime

from fastapi import APIRouter

from app.common.responses import HealthResponse
from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/live",
    response_model=HealthResponse,
    summary="Liveness check",
    description="Simple liveness probe used to confirm the API process is running.",
)
async def liveness_probe() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.project_name,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness check",
    description="Readiness probe used to confirm the API is ready to receive traffic.",
)
async def readiness_probe() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.project_name,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
    )
