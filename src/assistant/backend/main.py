import httpx
from google.genai import errors as google_genai_errors
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from assistant.backend.contracts.responses import ErrorResponse
from assistant.backend.shared.exceptions import (
    InvalidModelConfigurationError,
    InvalidImageInputError,
    UnsupportedRouteError,
    WeatherLocationNotFoundError,
    WeatherServiceError,
)
from assistant.backend.api.routers.assistant import router as assistant_router


def _error_response(
    *,
    status_code: int,
    error_type: str,
    message: str,
    provider: str | None = None,
    retryable: bool = False,
) -> JSONResponse:
    payload = ErrorResponse(
        error={
            "type": error_type,
            "message": message,
            "provider": provider,
            "retryable": retryable,
        }
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def create_app() -> FastAPI:
    app = FastAPI(title="Multimodal Assistant Backend")

    @app.exception_handler(InvalidModelConfigurationError)
    async def handle_invalid_model_configuration(
        request: Request, exc: InvalidModelConfigurationError
    ) -> JSONResponse:
        return _error_response(
            status_code=500,
            error_type="invalid_model_configuration",
            message=str(exc),
        )

    @app.exception_handler(UnsupportedRouteError)
    async def handle_unsupported_route(
        request: Request, exc: UnsupportedRouteError
    ) -> JSONResponse:
        return _error_response(
            status_code=400,
            error_type="unsupported_route",
            message=str(exc),
        )

    @app.exception_handler(InvalidImageInputError)
    async def handle_invalid_image_input(
        request: Request, exc: InvalidImageInputError
    ) -> JSONResponse:
        return _error_response(
            status_code=400,
            error_type="invalid_image_input",
            message=str(exc),
        )

    @app.exception_handler(WeatherLocationNotFoundError)
    async def handle_weather_location_not_found(
        request: Request, exc: WeatherLocationNotFoundError
    ) -> JSONResponse:
        return _error_response(
            status_code=404,
            error_type="weather_location_not_found",
            message=str(exc),
            provider="open-meteo",
        )

    @app.exception_handler(WeatherServiceError)
    async def handle_weather_service_error(
        request: Request, exc: WeatherServiceError
    ) -> JSONResponse:
        return _error_response(
            status_code=503,
            error_type="weather_service_error",
            message=str(exc),
            provider="open-meteo",
            retryable=True,
        )

    @app.exception_handler(google_genai_errors.ClientError)
    async def handle_google_client_error(
        request: Request, exc: google_genai_errors.ClientError
    ) -> JSONResponse:
        if exc.code in {401, 403}:
            return _error_response(
                status_code=502,
                error_type="google_ai_studio_authentication_error",
                message="Google AI Studio rejected the backend credentials.",
                provider="google_ai_studio",
            )
        if exc.code == 429:
            return _error_response(
                status_code=503,
                error_type="google_ai_studio_rate_limit_error",
                message="Google AI Studio quota or rate limit was exceeded.",
                provider="google_ai_studio",
                retryable=True,
            )
        return _error_response(
            status_code=502,
            error_type="google_ai_studio_client_error",
            message="A Google AI Studio client error occurred.",
            provider="google_ai_studio",
        )

    @app.exception_handler(google_genai_errors.ServerError)
    async def handle_google_server_error(
        request: Request, exc: google_genai_errors.ServerError
    ) -> JSONResponse:
        return _error_response(
            status_code=503,
            error_type="google_ai_studio_server_error",
            message="Google AI Studio returned a server-side error.",
            provider="google_ai_studio",
            retryable=True,
        )

    @app.exception_handler(google_genai_errors.APIError)
    async def handle_google_api_error(
        request: Request, exc: google_genai_errors.APIError
    ) -> JSONResponse:
        return _error_response(
            status_code=502,
            error_type="google_ai_studio_runtime_error",
            message="A Google AI Studio runtime error occurred.",
            provider="google_ai_studio",
        )

    @app.exception_handler(ChatGoogleGenerativeAIError)
    async def handle_langchain_google_error(
        request: Request, exc: ChatGoogleGenerativeAIError
    ) -> JSONResponse:
        message_text = str(exc)
        if "429" in message_text or "RESOURCE_EXHAUSTED" in message_text:
            return _error_response(
                status_code=503,
                error_type="google_ai_studio_rate_limit_error",
                message="Google AI Studio quota or rate limit was exceeded.",
                provider="google_ai_studio",
                retryable=True,
            )
        if "401" in message_text or "403" in message_text:
            return _error_response(
                status_code=502,
                error_type="google_ai_studio_authentication_error",
                message="Google AI Studio rejected the backend credentials.",
                provider="google_ai_studio",
            )
        return _error_response(
            status_code=502,
            error_type="google_ai_studio_runtime_error",
            message="A Google AI Studio runtime error occurred.",
            provider="google_ai_studio",
        )

    @app.exception_handler(httpx.ConnectError)
    async def handle_httpx_connect_error(
        request: Request, exc: httpx.ConnectError
    ) -> JSONResponse:
        return _error_response(
            status_code=503,
            error_type="google_ai_studio_connection_error",
            message="The backend could not reach Google AI Studio.",
            provider="google_ai_studio",
            retryable=True,
        )

    @app.exception_handler(httpx.TimeoutException)
    async def handle_httpx_timeout_error(
        request: Request, exc: httpx.TimeoutException
    ) -> JSONResponse:
        return _error_response(
            status_code=503,
            error_type="google_ai_studio_timeout_error",
            message="The backend timed out while waiting for Google AI Studio.",
            provider="google_ai_studio",
            retryable=True,
        )

    app.include_router(assistant_router)
    return app


app = create_app()
