from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.responses import ErrorBody, ErrorResponse
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int = HTTPStatus.BAD_REQUEST
    details: Any | None = None
    headers: dict[str, str] | None = None


def _request_id_from(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_payload(
    *,
    code: str,
    message: str,
    request_id: str | None,
    details: Any | None = None,
) -> dict[str, Any]:
    return ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            details=jsonable_encoder(details, custom_encoder={BaseException: str}),
            request_id=request_id,
        )
    ).model_dump(mode="json")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                code=exc.code,
                message=exc.message,
                request_id=_request_id_from(request),
                details=exc.details,
            ),
            headers=exc.headers,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                code=f"http_{exc.status_code}",
                message=str(exc.detail),
                request_id=_request_id_from(request),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            content=_error_payload(
                code="validation_error",
                message="Request validation failed.",
                request_id=_request_id_from(request),
                details=exc.errors(),
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        settings = get_settings()
        logger.exception(
            "unhandled_exception",
            path=str(request.url.path),
            method=request.method,
            request_id=_request_id_from(request),
        )
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content=_error_payload(
                code="internal_server_error",
                message="An unexpected error occurred." if settings.is_production else str(exc),
                request_id=_request_id_from(request),
            ),
        )
