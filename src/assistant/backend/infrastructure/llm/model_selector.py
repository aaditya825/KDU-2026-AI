from typing import Type

from pydantic import BaseModel

from assistant.backend.shared.exceptions import InvalidModelConfigurationError
from assistant.backend.shared.settings import AppSettings


class ModelSelector:
    """Choose the Gemini model for the text-only MVP flow."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    def select_default_text_model(self, output_schema: Type[BaseModel] | None = None):
        self.validate_configuration()

        from langchain_google_genai import ChatGoogleGenerativeAI

        model = ChatGoogleGenerativeAI(
            model=self._settings.assistant_model,
            google_api_key=(self._settings.gemini_api_key or "").strip(),
        )
        return model.with_structured_output(output_schema) if output_schema else model

    def select_tool_calling_model(self, tools: list):
        self.validate_configuration()

        from langchain_google_genai import ChatGoogleGenerativeAI

        model = ChatGoogleGenerativeAI(
            model=self._settings.assistant_model,
            google_api_key=(self._settings.gemini_api_key or "").strip(),
        )
        return model.bind_tools(tools)

    def active_model_name(self) -> str:
        return self._settings.assistant_model

    def validate_configuration(self) -> None:
        if not (self._settings.gemini_api_key or "").strip():
            raise InvalidModelConfigurationError(
                "GEMINI_API_KEY is required."
            )
