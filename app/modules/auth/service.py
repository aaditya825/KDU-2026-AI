from __future__ import annotations

from datetime import UTC, datetime

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.exceptions import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.models.user import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import RegisterUserRequest, TokenResponse


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AuthRepository(session)

    async def register_user(self, payload: RegisterUserRequest) -> User:
        normalized_email = payload.email.lower()
        existing_user = await self.repository.get_user_by_email(normalized_email)
        if existing_user is not None:
            raise AppError(
                code="user_already_exists",
                message="A user with this email already exists.",
                status_code=status.HTTP_409_CONFLICT,
            )

        try:
            user = await self.repository.create_user(
                email=normalized_email,
                password_hash=hash_password(payload.password),
                full_name=payload.full_name.strip(),
            )
            await self.session.commit()
            return user
        except IntegrityError as exc:
            await self.session.rollback()
            raise AppError(
                code="user_creation_failed",
                message="User could not be created.",
                status_code=status.HTTP_400_BAD_REQUEST,
            ) from exc

    async def login_user(self, *, email: str, password: str) -> TokenResponse:
        user = await self._authenticate_user(email=email, password=password)
        return await self._issue_token_pair(user)

    async def refresh_user_tokens(self, *, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, expected_type="refresh")

        jti = payload.get("jti")
        sub = payload.get("sub")
        if not isinstance(jti, str) or not isinstance(sub, str):
            raise AppError(
                code="invalid_refresh_token",
                message="Refresh token payload is invalid.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        stored_token = await self.repository.get_refresh_token_by_jti(jti)
        if stored_token is None:
            raise AppError(
                code="refresh_token_not_found",
                message="Refresh token is not recognized.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if stored_token.revoked_at is not None or stored_token.expires_at <= datetime.now(UTC):
            raise AppError(
                code="refresh_token_revoked",
                message="Refresh token is no longer valid.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if stored_token.token_hash != hash_token(refresh_token):
            raise AppError(
                code="refresh_token_mismatch",
                message="Refresh token is invalid.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        user = await self.repository.get_user_by_id(int(sub))
        if user is None:
            raise AppError(
                code="user_not_found",
                message="User no longer exists.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            raise AppError(
                code="inactive_user",
                message="User account is inactive.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        await self.repository.revoke_refresh_token(stored_token)
        token_response = await self._issue_token_pair(user)
        return token_response

    async def get_user_from_access_token(self, token: str) -> User:
        payload = decode_token(token, expected_type="access")
        sub = payload.get("sub")
        if not isinstance(sub, str):
            raise AppError(
                code="invalid_token_subject",
                message="Token subject is invalid.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        user = await self.repository.get_user_by_id(int(sub))
        if user is None:
            raise AppError(
                code="user_not_found",
                message="Authenticated user was not found.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        return user

    async def _authenticate_user(self, *, email: str, password: str) -> User:
        normalized_email = email.lower()
        user = await self.repository.get_user_by_email(normalized_email)
        if user is None or not verify_password(password, user.password_hash):
            raise AppError(
                code="invalid_credentials",
                message="Email or password is incorrect.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            raise AppError(
                code="inactive_user",
                message="User account is inactive.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return user

    async def _issue_token_pair(self, user: User) -> TokenResponse:
        access_token, access_expires_at = create_access_token(
            user_id=user.id,
            role=user.role,
        )
        refresh_token, jti, refresh_expires_at = create_refresh_token(
            user_id=user.id,
            role=user.role,
        )

        await self.repository.create_refresh_token(
            user_id=user.id,
            jti=jti,
            token_hash=hash_token(refresh_token),
            expires_at=refresh_expires_at,
        )
        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_at=access_expires_at,
            refresh_token_expires_at=refresh_expires_at,
        )


def user_has_role(user: User, role: UserRole) -> bool:
    return user.role == role
