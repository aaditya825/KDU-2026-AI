"""Reusable Streamlit UI components."""
from typing import Any

import streamlit as st

from src.trading_agent.infrastructure.currency_converter import get_currency_service
from src.trading_agent.ui.backend_client import refresh_portfolio_snapshot


def _status_chip(label: str, tone: str = "neutral") -> str:
    tone_styles = {
        "positive": "background:#001e11;color:#4edea3;border:1px solid #164734;",
        "warning": "background:#271500;color:#ffb95f;border:1px solid #6a4a1f;",
        "danger": "background:#2b0b10;color:#ffb4ab;border:1px solid #7a3138;",
        "neutral": "background:#112036;color:#bdc7d8;border:1px solid #27354c;",
    }
    style = tone_styles.get(tone, tone_styles["neutral"])
    return (
        f"<span style=\"display:inline-block;padding:6px 10px;{style}"
        "font-size:0.72rem;letter-spacing:0.08em;text-transform:uppercase;"
        "font-weight:700;border-radius:0;\">"
        f"{label}</span>"
    )


def _format_currency(amount: float | None, currency: str) -> str:
    converter = get_currency_service()
    symbol = converter.get_symbol(currency)
    if amount is None:
        return f"{symbol}0.00"
    return f"{symbol}{amount:,.2f}"


def _portfolio_totals() -> dict[str, Any]:
    portfolio = st.session_state.get("portfolio", {})
    prices = st.session_state.get("stock_prices", {})
    currency = st.session_state.get("currency", "USD")
    converter = get_currency_service()

    total_value_usd = sum(quantity * prices.get(symbol, 0.0) for symbol, quantity in portfolio.items()) if prices else 0.0
    state_total = st.session_state.get("total_value")
    if state_total is not None:
        total_value = state_total
    else:
        total_value = total_value_usd if currency == "USD" else converter.convert(total_value_usd, "USD", currency)

    return {
        "positions": len(portfolio),
        "shares": sum(portfolio.values()),
        "total_value": total_value,
        "currency": currency,
        "symbol": converter.get_symbol(currency),
    }


def _metric_card(title: str, value: str, subtitle: str = "", tone: str = "default") -> None:
    tone_accent = {
        "default": "#27354c",
        "positive": "#4edea3",
        "warning": "#ffb95f",
    }.get(tone, "#27354c")

    st.markdown(
        f"""
        <div style="
            background:#0d1c32;
            border:1px solid #27354c;
            padding:20px 18px;
            min-height:132px;
            display:flex;
            flex-direction:column;
            justify-content:space-between;
            border-radius:0;
            box-shadow:none;
        ">
            <div style="font-size:0.76rem;color:#8f9097;letter-spacing:0.08em;text-transform:uppercase;">{title}</div>
            <div style="font-size:2rem;line-height:1.1;font-weight:700;color:#d6e3ff;">{value}</div>
            <div style="font-size:0.84rem;color:{tone_accent};">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str) -> None:
    """Compatibility wrapper for the previous component API."""
    _metric_card(label, value)


def render_header() -> None:
    """Render the top terminal header."""
    totals = _portfolio_totals()
    pending_trade = st.session_state.get("pending_trade")
    approval_required = st.session_state.get("approval_required", False)

    status = "Awaiting approval" if approval_required else "Ready"
    tone = "warning" if approval_required else "positive"

    left_col, center_col, right_col = st.columns([3.2, 1.4, 1.1], gap="large")
    with left_col:
        st.markdown(
            """
            <div style="display:flex;flex-direction:column;gap:8px;">
                <div style="font-size:0.8rem;color:#8f9097;letter-spacing:0.12em;text-transform:uppercase;">
                    Equitas Terminal
                </div>
                <div style="font-size:2.45rem;line-height:1.0;font-weight:800;color:#d6e3ff;">
                    AI Trading Dashboard
                </div>
                <div style="max-width:760px;font-size:0.98rem;color:#8f9097;">
                    Approval-controlled trading workspace for portfolio value, currency conversion, and agent-driven execution.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with center_col:
        st.markdown(
            f"""
            <div style="background:#0d1c32;border:1px solid #27354c;padding:16px 18px;height:100%;">
                <div style="font-size:0.74rem;color:#8f9097;letter-spacing:0.08em;text-transform:uppercase;">Terminal Status</div>
                <div style="margin-top:14px;">{_status_chip(status, tone)}</div>
                <div style="margin-top:14px;font-size:0.92rem;color:#c5c6cd;">
                    {"Pending " + pending_trade.get("action", "").upper() if pending_trade else "No active trade queued"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right_col:
        currency = st.selectbox(
            "Display Currency",
            options=["USD", "INR", "EUR"],
            index=["USD", "INR", "EUR"].index(totals["currency"]),
            label_visibility="collapsed",
            key="header_currency_select",
        )
        st.session_state.currency = currency
        st.markdown(
            f"""
            <div style="margin-top:10px;font-size:0.8rem;color:#8f9097;letter-spacing:0.08em;text-transform:uppercase;">
                Active Currency
            </div>
            <div style="margin-top:6px;font-size:1.6rem;font-weight:700;color:#d6e3ff;">{currency}</div>
            """,
            unsafe_allow_html=True,
        )


def render_sidebar() -> None:
    """Render the left operations sidebar."""
    pending_trade = st.session_state.get("pending_trade")
    approval_required = st.session_state.get("approval_required", False)

    with st.sidebar:
        st.markdown(
            """
            <div style="padding-top:8px;padding-bottom:8px;">
                <div style="font-size:0.74rem;color:#8f9097;letter-spacing:0.10em;text-transform:uppercase;">Workspace</div>
                <div style="margin-top:6px;font-size:1.35rem;font-weight:700;color:#d6e3ff;">Trading Control</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(_status_chip("Pending Approval" if approval_required else "Live Session", "warning" if approval_required else "positive"), unsafe_allow_html=True)
        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="font-size:0.72rem;color:#8f9097;letter-spacing:0.08em;text-transform:uppercase;">Active modules</div>
            <div style="margin-top:10px;display:flex;flex-direction:column;gap:10px;">
                <div style="padding:10px 12px;background:#112036;border-left:3px solid #4edea3;color:#d6e3ff;">Portfolio Overview</div>
                <div style="padding:10px 12px;background:#0d1c32;border-left:3px solid #27354c;color:#bdc7d8;">Agent Console</div>
                <div style="padding:10px 12px;background:#0d1c32;border-left:3px solid #27354c;color:#bdc7d8;">Execution Approval</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="font-size:0.72rem;color:#8f9097;letter-spacing:0.08em;text-transform:uppercase;">Current trade</div>
            <div style="margin-top:10px;padding:14px 14px;background:#0d1c32;border:1px solid #27354c;color:#c5c6cd;">
                {f"{pending_trade.get('action', '').upper()} {pending_trade.get('quantity')} {pending_trade.get('symbol')}" if pending_trade else "No pending trade"}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)
        if st.button("Reset Session", use_container_width=True):
            from src.utils.session import clear_session

            clear_session()
            st.rerun()

        if st.button("Refresh Market Data", use_container_width=True):
            try:
                result = refresh_portfolio_snapshot(
                    thread_id=st.session_state.thread_id,
                    frontend_state={
                        "holdings": st.session_state.get("portfolio", {}),
                        "currency": st.session_state.get("currency", "USD"),
                        "stock_prices": st.session_state.get("stock_prices", {}),
                        "value_history": st.session_state.get("value_history", []),
                        "pending_trade": st.session_state.get("pending_trade"),
                        "requires_approval": st.session_state.get("approval_required", False),
                        "approval_granted": st.session_state.get("approval_granted"),
                    },
                )
                st.session_state.portfolio = result.get("holdings", {})
                st.session_state.stock_prices = result.get("stock_prices", {})
                st.session_state.total_value = result.get("total_value")
                st.session_state.currency = result.get("currency", st.session_state.get("currency", "USD"))
                st.session_state.value_history = result.get("value_history", [])
                st.session_state.observability = result.get("observability", {})
                st.session_state.market_data_initialized = True
                st.session_state.market_data_attempted = True
                st.session_state.market_data_error = None
                st.rerun()
            except Exception:
                st.session_state.market_data_error = "Unable to refresh live market data."

        error = st.session_state.get("market_data_error")
        if error:
            st.caption(error)
        else:
            st.caption("Use the assistant to value the portfolio, request trades, and approve or reject execution.")


def render_portfolio_summary() -> None:
    """Render top-level portfolio summary cards."""
    totals = _portfolio_totals()
    approval_required = st.session_state.get("approval_required", False)
    value_history = st.session_state.get("value_history", [])
    latest_action = value_history[-1]["action"].upper() if value_history else "No executions yet"

    col_one, col_two, col_three = st.columns(3, gap="large")
    with col_one:
        _metric_card(
            "Portfolio Value",
            _format_currency(totals["total_value"], totals["currency"]) if st.session_state.get("stock_prices") else "Awaiting data",
            "Live market value of all holdings" if st.session_state.get("stock_prices") else "Refresh or start backend to load prices",
            tone="positive" if totals["total_value"] > 0 else "default",
        )
    with col_two:
        _metric_card(
            "Open Positions",
            str(totals["positions"]),
            f"{totals['shares']} total shares across tracked symbols",
        )
    with col_three:
        _metric_card(
            "Execution State",
            "Awaiting approval" if approval_required else "No blockers",
            latest_action,
            tone="warning" if approval_required else "default",
        )


def render_approval_modal(trade: dict, stock_prices: dict) -> None:
    """Render approval controls for a pending trade."""
    action = str(trade.get("action", "trade")).upper()
    symbol = trade.get("symbol", "UNKNOWN")
    quantity = int(trade.get("quantity", 0))
    price = stock_prices.get(symbol, 0.0)
    total_cost = quantity * price

    st.markdown(
        f"""
        <div style="
            background:#271500;
            border:1px solid #6a4a1f;
            padding:18px 18px 20px 18px;
            margin-bottom:16px;
            border-radius:0;
        ">
            <div style="font-size:0.74rem;color:#ffb95f;letter-spacing:0.10em;text-transform:uppercase;">Approval Required</div>
            <div style="margin-top:10px;font-size:1.35rem;font-weight:700;color:#ffddb8;">{action} {quantity} {symbol}</div>
            <div style="margin-top:12px;color:#d6c2a0;line-height:1.7;">
                Price: ${price:.2f} per share<br/>
                Estimated total: ${total_cost:,.2f}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    approve_col, reject_col = st.columns(2, gap="small")
    with approve_col:
        if st.button("Approve Trade", use_container_width=True, type="primary"):
            st.session_state.approval_granted = True
            st.session_state.approval_required = False
            st.rerun()
    with reject_col:
        if st.button("Reject Trade", use_container_width=True):
            st.session_state.approval_granted = False
            st.session_state.approval_required = False
            st.rerun()


def render_observability_panel() -> None:
    """Render a compact observability card with only real backend data."""
    observability = st.session_state.get("observability", {}) or {}
    if not observability:
        st.markdown(
            """
            <div style="background:#0d1c32;border:1px solid #27354c;padding:18px;">
                <div style="font-size:0.74rem;color:#8f9097;letter-spacing:0.08em;text-transform:uppercase;">Observability</div>
                <div style="margin-top:14px;color:#c5c6cd;">No recent trace data yet.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    tracing_enabled = "Enabled" if observability.get("tracing_enabled") else "Disabled"
    st.markdown(
        f"""
        <div style="background:#0d1c32;border:1px solid #27354c;padding:18px;">
            <div style="font-size:0.74rem;color:#8f9097;letter-spacing:0.08em;text-transform:uppercase;">Observability</div>
            <div style="margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:12px 18px;">
                <div>
                    <div style="font-size:0.72rem;color:#8f9097;text-transform:uppercase;">Tracing</div>
                    <div style="margin-top:4px;color:#d6e3ff;font-weight:700;">{tracing_enabled}</div>
                </div>
                <div>
                    <div style="font-size:0.72rem;color:#8f9097;text-transform:uppercase;">Project</div>
                    <div style="margin-top:4px;color:#d6e3ff;font-weight:700;">{observability.get("project", "-")}</div>
                </div>
                <div>
                    <div style="font-size:0.72rem;color:#8f9097;text-transform:uppercase;">Tokens</div>
                    <div style="margin-top:4px;color:#d6e3ff;font-weight:700;">{observability.get("total_tokens", 0)}</div>
                </div>
                <div>
                    <div style="font-size:0.72rem;color:#8f9097;text-transform:uppercase;">Est. Cost</div>
                    <div style="margin-top:4px;color:#d6e3ff;font-weight:700;">${observability.get("estimated_cost_usd", 0):.6f}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
