import pytest
from pydantic import ValidationError

from app.modules.auth.schemas import RegisterUserRequest


def test_register_schema_rejects_password_without_uppercase() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RegisterUserRequest(
            email="schema@example.com",
            password="lowercase1!",
            full_name="Schema User",
        )

    assert "uppercase" in str(exc_info.value).lower()


def test_register_schema_rejects_password_without_digit() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RegisterUserRequest(
            email="schema@example.com",
            password="NoDigits!",
            full_name="Schema User",
        )

    assert "digit" in str(exc_info.value).lower()


def test_register_schema_accepts_strong_password() -> None:
    payload = RegisterUserRequest(
        email="schema@example.com",
        password="StrongPass1!",
        full_name="Schema User",
    )

    assert payload.email == "schema@example.com"
    assert payload.full_name == "Schema User"
