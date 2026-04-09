from typing import Any, cast

import pytest
from httpx import AsyncClient


async def register_user(
    client: AsyncClient,
    *,
    email: str = "errors@example.com",
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass1!",
            "full_name": "Error User",
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


@pytest.mark.asyncio
async def test_duplicate_registration_returns_conflict(client: AsyncClient) -> None:
    await register_user(client)

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "errors@example.com",
            "password": "StrongPass1!",
            "full_name": "Error User",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "user_already_exists"


@pytest.mark.asyncio
async def test_register_validation_errors_return_standardized_payload(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "weakpass",
            "full_name": "",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert isinstance(payload["error"]["details"], list)


@pytest.mark.asyncio
async def test_login_with_invalid_credentials_returns_unauthorized(
    client: AsyncClient,
) -> None:
    await register_user(client)

    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "errors@example.com",
            "password": "WrongPass1!",
        },
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_unauthorized(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "malformed-token"},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "invalid_token"


@pytest.mark.asyncio
async def test_auth_me_requires_bearer_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "http_401"


@pytest.mark.asyncio
async def test_auth_me_rejects_invalid_bearer_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "invalid_token"


@pytest.mark.asyncio
async def test_registration_normalizes_email_and_login_accepts_lowercase(
    client: AsyncClient,
) -> None:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "MixedCase@Example.com",
            "password": "StrongPass1!",
            "full_name": "Mixed User",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == "mixedcase@example.com"

    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "mixedcase@example.com",
            "password": "StrongPass1!",
        },
    )
    assert login_response.status_code == 200
