"""Portfolio visualization components."""
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.trading_agent.infrastructure.currency_converter import get_currency_service
from src.utils.logger import logger


def _portfolio_dataframe() -> pd.DataFrame:
    portfolio = st.session_state.get("portfolio", {})
    prices = st.session_state.get("stock_prices", {})
    total_value_usd = sum(quantity * prices.get(symbol, 0.0) for symbol, quantity in portfolio.items())

    rows = []
    for symbol, quantity in portfolio.items():
        price = prices.get(symbol, 0.0)
        market_value = quantity * price
        allocation = (market_value / total_value_usd * 100) if total_value_usd > 0 else 0.0
        rows.append(
            {
                "Symbol": symbol,
                "Quantity": quantity,
                "Last Price (USD)": round(price, 2),
                "Market Value (USD)": round(market_value, 2),
                "Allocation %": round(allocation, 1),
            }
        )

    return pd.DataFrame(rows)


def _dark_chart_layout(fig: Any) -> None:
    fig.update_layout(
        paper_bgcolor="#0d1c32",
        plot_bgcolor="#0d1c32",
        font_color="#d6e3ff",
        margin=dict(l=12, r=12, t=32, b=12),
    )


def render_portfolio_dashboard() -> None:
    """Render only the necessary portfolio table and charts."""
    portfolio = st.session_state.get("portfolio", {})
    prices = st.session_state.get("stock_prices", {})
    value_history = st.session_state.get("value_history", [])
    currency = st.session_state.get("currency", "USD")

    if not portfolio:
        st.markdown(
            """
            <div style="background:#0d1c32;border:1px solid #27354c;padding:24px;color:#c5c6cd;">
                No holdings yet. Use the trading assistant to place a buy order and populate the dashboard.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if not prices:
        st.markdown(
            """
            <div style="background:#0d1c32;border:1px solid #27354c;padding:24px;color:#c5c6cd;">
                Market data has not been loaded yet. Use <strong>Refresh Market Data</strong> or start the backend to populate live portfolio values.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    try:
        dataframe = _portfolio_dataframe()
        converter = get_currency_service()
        currency_symbol = converter.get_symbol(currency)

        top_left, top_right = st.columns([1.35, 1], gap="large")

        with top_left:
            st.markdown(
                """
                <div style="font-size:0.82rem;color:#8f9097;letter-spacing:0.10em;text-transform:uppercase;margin-bottom:12px;">
                    Holdings
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.dataframe(
                dataframe,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Symbol": st.column_config.TextColumn(width="small"),
                    "Quantity": st.column_config.NumberColumn(width="small"),
                    "Last Price (USD)": st.column_config.NumberColumn(format="$%.2f"),
                    "Market Value (USD)": st.column_config.NumberColumn(format="$%.2f"),
                    "Allocation %": st.column_config.ProgressColumn(
                        "Allocation %",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                    ),
                },
            )

        with top_right:
            st.markdown(
                """
                <div style="font-size:0.82rem;color:#8f9097;letter-spacing:0.10em;text-transform:uppercase;margin-bottom:12px;">
                    Allocation
                </div>
                """,
                unsafe_allow_html=True,
            )
            pie_chart = px.pie(
                dataframe,
                values="Market Value (USD)",
                names="Symbol",
                hole=0.55,
                color_discrete_sequence=["#4edea3", "#ffb95f", "#d6e3ff", "#5f89ff", "#7bd7c1", "#ff8f6b"],
            )
            pie_chart.update_traces(
                textposition="inside",
                textfont_size=12,
                textinfo="percent",
                hovertemplate="%{label}: $%{value:,.2f}<extra></extra>",
            )
            _dark_chart_layout(pie_chart)
            pie_chart.update_layout(showlegend=True, height=360)
            st.plotly_chart(pie_chart, use_container_width=True)

        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="font-size:0.82rem;color:#8f9097;letter-spacing:0.10em;text-transform:uppercase;margin-bottom:12px;">
                Portfolio Performance
            </div>
            """,
            unsafe_allow_html=True,
        )
        if value_history:
            history_df = pd.DataFrame(value_history)
            if currency != "USD" and "value" in history_df:
                history_df["value"] = history_df["value"].apply(lambda amount: converter.convert(amount, "USD", currency))

            line_chart = go.Figure()
            line_chart.add_trace(
                go.Scatter(
                    x=list(range(1, len(history_df) + 1)),
                    y=history_df["value"],
                    mode="lines+markers",
                    line=dict(color="#4edea3", width=3),
                    marker=dict(size=8, color="#4edea3"),
                    hovertemplate=f"{currency_symbol}%{{y:,.2f}}<extra></extra>",
                    name="Portfolio Value",
                )
            )
            line_chart.update_layout(
                xaxis_title="Executed Trades",
                yaxis_title=f"Portfolio Value ({currency})",
                height=320,
                xaxis=dict(showgrid=False, color="#8f9097"),
                yaxis=dict(gridcolor="#27354c", color="#8f9097"),
            )
            _dark_chart_layout(line_chart)
            st.plotly_chart(line_chart, use_container_width=True)
        else:
            st.markdown(
                """
                <div style="background:#0d1c32;border:1px solid #27354c;padding:18px;color:#c5c6cd;">
                    Performance history will appear after executed trades.
                </div>
                """,
                unsafe_allow_html=True,
            )
    except Exception as exc:  # pragma: no cover - UI safeguard
        logger.error("Error rendering portfolio dashboard: %s", exc)
        st.error(f"Error rendering dashboard: {exc}")
