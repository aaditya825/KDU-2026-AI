import pytest

from assistant.backend.shared.exceptions import InvalidModelConfigurationError
from assistant.backend.shared.settings import AppSettings
from assistant.backend.infrastructure.llm.model_selector import ModelSelector


def test_model_selector_rejects_missing_gemini_key() -> None:
    selector = ModelSelector(AppSettings(gemini_api_key=None))

    with pytest.raises(InvalidModelConfigurationError):
        selector.validate_configuration()


def test_model_selector_accepts_gemini_with_key() -> None:
    selector = ModelSelector(
        AppSettings(
            gemini_api_key="gemini-key",
            assistant_model="gemini-2.5-flash",
        )
    )

    selector.validate_configuration()

    assert selector.active_model_name() == "gemini-2.5-flash"
