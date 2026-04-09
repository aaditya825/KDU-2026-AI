from fastapi import APIRouter

from app.common.responses import VersionResponse
from app.core.config import get_settings

router = APIRouter(prefix="/version", tags=["meta"])


@router.get(
    "",
    response_model=VersionResponse,
    summary="Service version",
    description="Returns service version and environment metadata for operational visibility.",
)
async def service_version() -> VersionResponse:
    settings = get_settings()
    return VersionResponse(
        service=settings.project_name,
        version=settings.version,
        environment=settings.environment,
    )
