from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.router import router as api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import register_middleware
from app.core.rate_limit import InMemoryRateLimiter
from app.db.session import dispose_engine

settings = get_settings()
configure_logging(settings)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "application_startup",
        environment=settings.environment,
        version=settings.version,
    )
    yield
    await dispose_engine()
    logger.info("application_shutdown")


def create_application(app_settings: Settings | None = None) -> FastAPI:
    current_settings = app_settings or settings
    application = FastAPI(
        title=current_settings.project_name,
        description=current_settings.project_description,
        version=current_settings.version,
        debug=current_settings.debug,
        docs_url=current_settings.docs_url,
        redoc_url=current_settings.redoc_url,
        lifespan=lifespan,
    )
    application.state.auth_rate_limiter = InMemoryRateLimiter()
    register_middleware(application, current_settings)
    register_exception_handlers(application)
    application.include_router(api_router, prefix=current_settings.api_v1_prefix)
    return application


app = create_application()
