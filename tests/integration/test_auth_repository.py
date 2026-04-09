from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.repository import AuthRepository


@pytest.mark.asyncio
async def test_repository_creates_and_fetches_user(db_session: AsyncSession) -> None:
    repository = AuthRepository(db_session)

    created_user = await repository.create_user(
        email="repo@example.com",
        password_hash="hashed-password",
        full_name="Repository User",
    )
    await db_session.commit()

    fetched_user = await repository.get_user_by_email("repo@example.com")

    assert fetched_user is not None
    assert fetched_user.id == created_user.id
    assert fetched_user.full_name == "Repository User"


@pytest.mark.asyncio
async def test_repository_creates_and_revokes_refresh_token(db_session: AsyncSession) -> None:
    repository = AuthRepository(db_session)
    user = await repository.create_user(
        email="repo-token@example.com",
        password_hash="hashed-password",
        full_name="Token User",
    )
    await db_session.flush()

    refresh_token = await repository.create_refresh_token(
        user_id=user.id,
        jti="test-jti",
        token_hash="hashed-token",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    await db_session.commit()

    stored_token = await repository.get_refresh_token_by_jti("test-jti")
    assert stored_token is not None
    assert stored_token.id == refresh_token.id
    assert stored_token.revoked_at is None

    await repository.revoke_refresh_token(stored_token)
    await db_session.commit()

    revoked_token = await repository.get_refresh_token_by_jti("test-jti")
    assert revoked_token is not None
    assert revoked_token.revoked_at is not None
