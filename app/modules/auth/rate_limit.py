from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, status

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.rate_limit import InMemoryRateLimiter


def _client_identifier_from(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown-client"


async def enforce_auth_rate_limit(request: Request) -> None:
    limiter: InMemoryRateLimiter = request.app.state.auth_rate_limiter
    settings = get_settings()
    key = f"{request.method}:{request.url.path}:{_client_identifier_from(request)}"
    retry_after = limiter.check(key, settings.rate_limit_auth)

    if retry_after is not None:
        raise AppError(
            code="rate_limit_exceeded",
            message="Rate limit exceeded. Please try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry_after)},
        )


AuthRateLimitDependency = Annotated[None, Depends(enforce_auth_rate_limit)]
