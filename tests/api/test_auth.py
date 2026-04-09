from typing import Any, cast

import pytest
from httpx import AsyncClient


async def register_user(client: AsyncClient, *, email: str = "test@example.com") -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass1!",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


async def login_user(client: AsyncClient, *, email: str = "test@example.com") -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": "StrongPass1!",
        },
    )
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


@pytest.mark.asyncio
async def test_register_user_returns_public_profile(client: AsyncClient) -> None:
    payload = await register_user(client)

    assert payload["email"] == "test@example.com"
    assert payload["role"] == "user"
    assert payload["is_active"] is True
    assert "password" not in payload


@pytest.mark.asyncio
async def test_login_and_me_flow(client: AsyncClient) -> None:
    await register_user(client)
    tokens = await login_user(client)

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "test@example.com"
    assert payload["role"] == "user"


@pytest.mark.asyncio
async def test_refresh_rotates_tokens_and_invalidates_old_refresh_token(
    client: AsyncClient,
) -> None:
    await register_user(client)
    tokens = await login_user(client)

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    refreshed_tokens = refresh_response.json()
    assert refreshed_tokens["access_token"] != tokens["access_token"]
    assert refreshed_tokens["refresh_token"] != tokens["refresh_token"]

    second_refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert second_refresh_response.status_code == 401
    assert second_refresh_response.json()["error"]["code"] == "refresh_token_revoked"
