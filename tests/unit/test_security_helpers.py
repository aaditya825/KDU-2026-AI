import pytest

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


def test_hash_password_and_verify_password_round_trip() -> None:
    password = "StrongPass1!"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash) is True
    assert verify_password("WrongPass1!", password_hash) is False


def test_access_token_contains_expected_claims() -> None:
    token, _ = create_access_token(user_id=42, role=UserRole.ADMIN)
    payload = decode_token(token, expected_type="access")

    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert isinstance(payload["jti"], str)


def test_access_tokens_are_unique_across_fast_reissuance() -> None:
    first_token, _ = create_access_token(user_id=42, role=UserRole.ADMIN)
    second_token, _ = create_access_token(user_id=42, role=UserRole.ADMIN)

    assert first_token != second_token


def test_refresh_token_contains_jti_and_expected_claims() -> None:
    token, jti, _ = create_refresh_token(user_id=99, role=UserRole.USER)
    payload = decode_token(token, expected_type="refresh")

    assert payload["sub"] == "99"
    assert payload["role"] == "user"
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_decode_token_rejects_wrong_expected_type() -> None:
    access_token, _ = create_access_token(user_id=1, role=UserRole.USER)

    with pytest.raises(AppError) as exc_info:
        decode_token(access_token, expected_type="refresh")

    assert exc_info.value.code == "invalid_token_type"


def test_hash_token_is_stable_for_same_input() -> None:
    token = "example-token"

    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != hash_token("different-token")
