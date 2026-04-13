"""Compatibility wrapper for Streamlit UI components."""
from src.trading_agent.ui.components import (
    render_approval_modal,
    render_header,
    render_metric_card,
    render_portfolio_summary,
    render_sidebar,
)

__all__ = [
    "render_header",
    "render_sidebar",
    "render_metric_card",
    "render_portfolio_summary",
    "render_approval_modal",
]
