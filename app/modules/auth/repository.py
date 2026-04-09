from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        result = await self.session.scalars(statement)
        return result.first()

    async def get_user_by_id(self, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id)
        result = await self.session.scalars(statement)
        return result.first()

    async def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def create_refresh_token(
        self,
        *,
        user_id: int,
        jti: str,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        refresh_token = RefreshToken(
            user_id=user_id,
            jti=jti,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(refresh_token)
        await self.session.flush()
        await self.session.refresh(refresh_token)
        return refresh_token

    async def get_refresh_token_by_jti(self, jti: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await self.session.scalars(statement)
        return result.first()

    async def revoke_refresh_token(self, refresh_token: RefreshToken) -> None:
        refresh_token.revoked_at = datetime.now(UTC)
        await self.session.flush()
