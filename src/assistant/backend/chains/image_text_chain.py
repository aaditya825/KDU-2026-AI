from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory

from assistant.backend.contracts.responses import ImageTextResult


class ImageTextChainBuilder:
    """Build the LCEL chain for image-analysis responses."""

    def __init__(self, prompt_factory, model_selector, message_history_store) -> None:
        self._prompt_factory = prompt_factory
        self._model_selector = model_selector
        self._message_history_store = message_history_store

    def build(self) -> Runnable:
        model = self._model_selector.select_default_text_model(
            output_schema=ImageTextResult
        )
        chain = RunnableLambda(
            lambda state: [
                SystemMessage(
                    content=self._prompt_factory.build_image_analysis_system_prompt(
                        user_name=state.get("user_name", "User"),
                        communication_style=state.get("communication_style", "neutral"),
                        expertise_level=state.get("expertise_level", "general"),
                        preferred_response_length=state.get(
                            "preferred_response_length", "medium"
                        ),
                    )
                ),
                *state["history"],
                state["current_input"],
            ]
        ) | model
        return RunnableWithMessageHistory(
            chain,
            get_session_history=self._message_history_store.get_session_history,
            input_messages_key="current_input",
            history_messages_key="history",
        )
