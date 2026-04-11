from assistant.backend.application.services.message_history_store import MessageHistoryStore


def test_message_history_store_returns_same_history_for_same_session() -> None:
    store = MessageHistoryStore()

    first = store.get_session_history("session-1")
    second = store.get_session_history("session-1")

    assert first is second


def test_message_history_store_returns_different_history_for_different_sessions() -> None:
    store = MessageHistoryStore()

    first = store.get_session_history("session-1")
    second = store.get_session_history("session-2")

    assert first is not second
