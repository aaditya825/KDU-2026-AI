from langchain_core.runnables import Runnable
from langchain_core.runnables.history import RunnableWithMessageHistory

from assistant.backend.contracts.responses import GeneralTextResult


class GeneralTextChainBuilder:
    """Build the active LCEL chain for the general text route."""

    def __init__(self, prompt_factory, model_selector, message_history_store) -> None:
        self._prompt_factory = prompt_factory
        self._model_selector = model_selector
        self._message_history_store = message_history_store

    def build(self) -> Runnable:
        prompt = self._prompt_factory.build_general_text_prompt()
        model = self._model_selector.select_default_text_model(
            output_schema=GeneralTextResult
        )
        chain = prompt | model
        return RunnableWithMessageHistory(
            chain,
            get_session_history=self._message_history_store.get_session_history,
            input_messages_key="message",
            history_messages_key="history",
        )
