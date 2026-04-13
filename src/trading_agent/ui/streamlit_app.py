"""Stock Trading Agent Streamlit entry point."""
import os
import sys

import streamlit as st

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests

from src.trading_agent.ui.backend_client import refresh_portfolio_snapshot
from src.trading_agent.ui.chat_interface import render_chat
from src.trading_agent.ui.components import (
    render_header,
    render_observability_panel,
    render_portfolio_summary,
    render_sidebar,
)
from src.trading_agent.ui.portfolio_viz import render_portfolio_dashboard
from src.utils.logger import logger
from src.utils.session import init_session_state

st.set_page_config(
    page_title="Stock Trading Agent",
    page_icon="ST",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    html, body, #root, .stApp, [data-testid="stApp"], [data-testid="stAppViewContainer"],
    [data-testid="stMain"], [data-testid="stMainBlockContainer"], .main, .block-container,
    section[data-testid="stSidebar"], [data-testid="stSidebar"] {
        background: #041329 !important;
        color: #d6e3ff !important;
        font-family: "Inter", sans-serif !important;
    }
    [data-testid="stSidebar"] {
        border-right: 1px solid #112036 !important;
    }
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
        max-width: 1440px;
    }
    h1, h2, h3 {
        font-family: "Segoe UI", "Inter", sans-serif;
        color: #d6e3ff;
        letter-spacing: -0.02em;
    }
    p, div, span, label, small {
        color: #c5c6cd;
    }
    header[data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton, button[kind="header"],
    [data-testid="stDecoration"], #MainMenu, footer {
        display: none !important;
        visibility: hidden !important;
    }
    [data-testid="stMetric"] {
        background: transparent;
    }
    .stButton > button, .stDownloadButton > button {
        border-radius: 0 !important;
        border: 1px solid #27354c !important;
        background: #0d1c32 !important;
        color: #d6e3ff !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"] {
        background: #4edea3 !important;
        color: #003824 !important;
        border-color: #4edea3 !important;
    }
    .stChatInput textarea, .stTextInput input {
        color: #d6e3ff !important;
    }
    div[data-testid="stChatMessage"] {
        background: #0d1c32;
        border: 1px solid #27354c;
        border-radius: 0;
        padding: 0.5rem 0.75rem;
    }
    .stChatInput > div {
        background: #010e24;
        border: 1px solid #27354c;
        border-radius: 0;
    }
    div[data-baseweb="select"] > div {
        background: #0d1c32 !important;
        border-radius: 0 !important;
        border-color: #27354c !important;
    }
    .stDataFrame, .stTable {
        border: 1px solid #27354c;
    }
    [data-testid="stMarkdownContainer"] p {
        color: #c5c6cd !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


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


def _apply_refresh_result(result: dict) -> None:
    st.session_state.portfolio = result.get("holdings", {})
    st.session_state.stock_prices = result.get("stock_prices", {})
    st.session_state.value_history = result.get("value_history", [])
    st.session_state.total_value = result.get("total_value")
    st.session_state.currency = result.get("currency", st.session_state.get("currency", "USD"))
    st.session_state.pending_trade = result.get("pending_trade")
    st.session_state.approval_required = bool(result.get("requires_approval"))
    st.session_state.approval_granted = result.get("approval_granted")
    st.session_state.observability = result.get("observability", {})
    st.session_state.market_data_initialized = True
    st.session_state.market_data_error = None


def _ensure_dashboard_data() -> None:
    should_refresh = (
        st.session_state.get("portfolio")
        and not st.session_state.get("market_data_initialized")
        and not st.session_state.get("market_data_attempted")
        and not st.session_state.get("pending_trade")
    )
    if not should_refresh:
        return

    try:
        result = refresh_portfolio_snapshot(
            thread_id=st.session_state.thread_id,
            frontend_state=_frontend_state_payload(),
        )
        _apply_refresh_result(result)
    except requests.RequestException as exc:
        logger.warning("Initial dashboard refresh failed: %s", exc)
        st.session_state.market_data_error = "Backend unavailable. Start FastAPI backend to load live portfolio data."
    finally:
        st.session_state.market_data_attempted = True


def main() -> None:
    """Render the Streamlit application."""
    logger.info("Starting Streamlit application")
    init_session_state()
    _ensure_dashboard_data()

    render_sidebar()
    render_header()
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    render_portfolio_summary()
    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

    main_col, side_col = st.columns([1.7, 1], gap="large")
    with main_col:
        render_portfolio_dashboard()

    with side_col:
        st.markdown(
            """
            <div style="font-size:0.82rem;color:#8f9097;letter-spacing:0.10em;text-transform:uppercase;margin-bottom:12px;">
                Agent Console
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_chat()
        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
        render_observability_panel()


if __name__ == "__main__":
    main()
