from typing import Any, cast

import pytest
from httpx import AsyncClient, Response


def assert_security_headers(response: Response) -> None:
    headers = response.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["x-xss-protection"] == "0"
    assert "content-security-policy" in headers
    assert "default-src 'none'" in headers["content-security-policy"]


async def register_user(
    client: AsyncClient,
    email: str = "hardening@example.com",
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass1!",
            "full_name": "Security User",
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


async def login_user(
    client: AsyncClient,
    email: str = "hardening@example.com",
) -> dict[str, Any]:
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
async def test_security_headers_are_present_on_health_and_version_endpoints(
    client: AsyncClient,
) -> None:
    live_response = await client.get("/api/v1/health/live")
    version_response = await client.get("/api/v1/version")

    assert live_response.status_code == 200
    assert version_response.status_code == 200
    assert_security_headers(live_response)
    assert_security_headers(version_response)


@pytest.mark.asyncio
async def test_security_headers_are_present_on_success_and_error_auth_responses(
    client: AsyncClient,
) -> None:
    await register_user(client)

    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "hardening@example.com",
            "password": "StrongPass1!",
        },
    )
    invalid_login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "hardening@example.com",
            "password": "WrongPass1!",
        },
    )

    assert login_response.status_code == 200
    assert invalid_login_response.status_code == 401
    assert_security_headers(login_response)
    assert_security_headers(invalid_login_response)


@pytest.mark.asyncio
async def test_login_endpoint_is_rate_limited_and_returns_standardized_429(
    client: AsyncClient,
) -> None:
    responses = []
    for _ in range(6):
        responses.append(
            await client.post(
                "/api/v1/auth/login",
                data={
                    "username": "missing@example.com",
                    "password": "WrongPass1!",
                },
            )
        )

    final_response = responses[-1]
    assert final_response.status_code == 429
    payload = final_response.json()
    assert payload["error"]["code"] == "rate_limit_exceeded"
    assert "rate" in payload["error"]["message"].lower()
    assert "retry-after" in final_response.headers
    assert_security_headers(final_response)


@pytest.mark.asyncio
async def test_register_endpoint_is_rate_limited(client: AsyncClient) -> None:
    final_response = None
    for index in range(6):
        final_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"user{index}@example.com",
                "password": "StrongPass1!",
                "full_name": f"User {index}",
            },
        )

    assert final_response is not None
    assert final_response.status_code == 429
    assert final_response.json()["error"]["code"] == "rate_limit_exceeded"
    assert_security_headers(final_response)


@pytest.mark.asyncio
async def test_refresh_endpoint_is_rate_limited(client: AsyncClient) -> None:
    final_response = None
    for _ in range(6):
        final_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not-a-valid-token"},
        )

    assert final_response is not None
    assert final_response.status_code == 429
    assert final_response.json()["error"]["code"] == "rate_limit_exceeded"
    assert_security_headers(final_response)


@pytest.mark.asyncio
async def test_health_and_version_endpoints_are_not_affected_by_auth_rate_limit(
    client: AsyncClient,
) -> None:
    for _ in range(8):
        health_response = await client.get("/api/v1/health/live")
        version_response = await client.get("/api/v1/version")
        assert health_response.status_code == 200
        assert version_response.status_code == 200


@pytest.mark.asyncio
async def test_auth_me_still_works_with_security_headers(client: AsyncClient) -> None:
    await register_user(client)
    tokens = await login_user(client)

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "hardening@example.com"
    assert_security_headers(response)
