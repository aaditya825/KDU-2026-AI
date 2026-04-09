from __future__ import annotations

from typing import Any, cast

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.security import hash_password
from app.db.models.user import User


async def create_user(
    db_session: AsyncSession,
    *,
    email: str,
    role: UserRole,
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password("StrongPass1!"),
        full_name="Example User",
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def login_user(client: AsyncClient, *, email: str) -> dict[str, Any]:
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
async def test_admin_users_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/users")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "http_401"


@pytest.mark.asyncio
async def test_admin_users_rejects_non_admin_users(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="member@example.com", role=UserRole.USER)
    tokens = await login_user(client, email="member@example.com")

    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


@pytest.mark.asyncio
async def test_admin_users_allows_active_admin_and_excludes_sensitive_fields(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await create_user(db_session, email="member@example.com", role=UserRole.USER)
    await create_user(db_session, email="admin@example.com", role=UserRole.ADMIN)
    tokens = await login_user(client, email="admin@example.com")

    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [user["email"] for user in payload] == ["member@example.com", "admin@example.com"]
    assert all("password_hash" not in user for user in payload)
    assert all("refresh_tokens" not in user for user in payload)
    assert {user["role"] for user in payload} == {"user", "admin"}
