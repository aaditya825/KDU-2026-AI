from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

import jwt
from fastapi import status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.common.enums import UserRole
from app.core.config import get_settings
from app.core.exceptions import AppError

password_hasher = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def _encode_token(payload: dict[str, Any]) -> str:
    settings = get_settings()
    return jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(*, user_id: int, role: UserRole) -> tuple[str, datetime]:
    settings = get_settings()
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "type": "access",
        "iat": issued_at,
        "jti": str(uuid4()),
        "exp": expires_at,
    }
    return _encode_token(payload), expires_at


def create_refresh_token(*, user_id: int, role: UserRole) -> tuple[str, str, datetime]:
    settings = get_settings()
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(days=settings.refresh_token_expire_days)
    jti = str(uuid4())
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "type": "refresh",
        "iat": issued_at,
        "jti": jti,
        "exp": expires_at,
    }
    return _encode_token(payload), jti, expires_at


def decode_token(token: str, *, expected_type: Literal["access", "refresh"]) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise AppError(
            code="invalid_token",
            message="Token is invalid or expired.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from exc

    token_type = payload.get("type")
    if token_type != expected_type:
        raise AppError(
            code="invalid_token_type",
            message=f"Expected a {expected_type} token.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return payload


def hash_token(token: str) -> str:
    secret = get_settings().secret_key.get_secret_value().encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()
