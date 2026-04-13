"""Chat interface for the Streamlit application."""
import requests
import streamlit as st

from src.trading_agent.ui.backend_client import send_approval, send_chat_message
from src.trading_agent.ui.components import render_approval_modal
from src.utils.logger import logger


def _update_session_from_result(result: dict) -> None:
    st.session_state.portfolio = result.get("holdings", {})
    st.session_state.stock_prices = result.get("stock_prices", {})
    st.session_state.value_history = result.get("value_history", [])
    st.session_state.total_value = result.get("total_value")
    st.session_state.currency = result.get("currency", st.session_state.get("currency", "USD"))
    st.session_state.pending_trade = result.get("pending_trade")
    st.session_state.approval_required = bool(result.get("requires_approval"))
    st.session_state.approval_granted = result.get("approval_granted")
    st.session_state.observability = result.get("observability", {})


def _frontend_state_payload() -> dict:
    return {
        "holdings": st.session_state.get("portfolio", {}),
        "currency": st.session_state.get("currency", "USD"),
        "stock_prices": st.session_state.get("stock_prices", {}),
        "value_history": st.session_state.get("value_history", []),
        "pending_trade": st.session_state.get("pending_trade"),
        "requires_approval": st.session_state.get("approval_required", False),
        "approval_granted": st.session_state.get("approval_granted"),
    }


def render_chat() -> None:
    """Render the chat panel with history and input."""
    with st.container():
        for message in st.session_state.get("messages", []):
            with st.chat_message(message.get("role", "user")):
                st.write(message.get("content", ""))

    st.divider()

    if (
        st.session_state.get("pending_trade")
        and st.session_state.get("approval_granted") is not None
        and not st.session_state.get("approval_required")
    ):
        try:
            with st.spinner("Finalizing trade..."):
                result = send_approval(
                    thread_id=st.session_state.thread_id,
                    approved=bool(st.session_state.get("approval_granted")),
                )
                _update_session_from_result(result)

                assistant_message = result.get("assistant_message")
                if assistant_message:
                    st.session_state.messages.append({"role": "assistant", "content": assistant_message})
                st.rerun()
        except requests.RequestException as exc:
            logger.error("Backend unavailable during approval resume: %s", exc)
            st.error("Backend is unavailable. Start the FastAPI backend and try again.")
            st.session_state.approval_granted = None
        return

    if st.session_state.get("approval_required"):
        if st.session_state.get("pending_trade"):
            render_approval_modal(
                st.session_state.pending_trade,
                st.session_state.get("stock_prices", {}),
            )
        return

    prompt = st.chat_input("Ask about your portfolio or trade stocks...")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    try:
        with st.spinner("Thinking..."):
            result = send_chat_message(
                thread_id=st.session_state.thread_id,
                message=prompt,
                frontend_state=_frontend_state_payload(),
            )
        _update_session_from_result(result)

        assistant_message = result.get("assistant_message")
        if assistant_message:
            with st.chat_message("assistant"):
                st.write(assistant_message)
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})

        if result.get("requires_approval"):
            st.rerun()
    except requests.RequestException as exc:
        logger.error("Backend unavailable during chat request: %s", exc)
        st.error("Backend is unavailable. Start the FastAPI backend and try again.")
    except Exception as exc:  # pragma: no cover - UI safeguard
        logger.error("Chat flow failed: %s", exc)
        st.error(f"Chat flow failed: {exc}")
