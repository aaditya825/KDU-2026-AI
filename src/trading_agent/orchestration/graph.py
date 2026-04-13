"""LangGraph assembly and invocation APIs."""
from datetime import datetime
from typing import Any

from langgraph.graph import END, StateGraph

from src.trading_agent.domain import PortfolioState
from src.trading_agent.infrastructure import resolve_checkpointer
from src.trading_agent.orchestration.nodes import (
    analyze_request,
    calculate_portfolio,
    convert_currency,
    execute_trade,
    fetch_stock_price,
    human_approval_gate,
)
from src.trading_agent.orchestration.routes import (
    route_after_analyze,
    route_after_approval,
    route_after_calculate,
    route_after_execute,
)
from src.utils.logger import logger

_graph = None


def create_agent_graph():
    """Build and compile the trading workflow graph."""
    logger.info("Creating LangGraph agent...")
    workflow = StateGraph(PortfolioState)

    workflow.add_node("analyze", analyze_request)
    workflow.add_node("fetch_stock_price", fetch_stock_price)
    workflow.add_node("calculate_portfolio", calculate_portfolio)
    workflow.add_node("convert_currency", convert_currency)
    workflow.add_node("human_approval_gate", human_approval_gate)
    workflow.add_node("execute_trade", execute_trade)
    workflow.set_entry_point("analyze")

    workflow.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {
            "fetch_stock_price": "fetch_stock_price",
            "calculate_portfolio": "calculate_portfolio",
            "convert_currency": "convert_currency",
            "end": END,
        },
    )

    workflow.add_edge("fetch_stock_price", "calculate_portfolio")

    workflow.add_conditional_edges(
        "calculate_portfolio",
        route_after_calculate,
        {
            "human_approval_gate": "human_approval_gate",
            "execute_trade": "execute_trade",
            "convert_currency": "convert_currency",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "human_approval_gate",
        route_after_approval,
        {"execute_trade": "execute_trade"},
    )

    workflow.add_conditional_edges(
        "execute_trade",
        route_after_execute,
        {
            "convert_currency": "convert_currency",
            "end": END,
        },
    )

    workflow.add_edge("convert_currency", END)

    app = workflow.compile(
        checkpointer=resolve_checkpointer(),
        interrupt_before=["human_approval_gate"],
    )
    logger.info("Graph compiled successfully")
    return app


def get_graph():
    """Return singleton compiled graph."""
    global _graph
    if _graph is None:
        _graph = create_agent_graph()
    return _graph


def invoke_agent(state: Any, thread_id: str, stream: bool = False):
    """Invoke graph by thread and state payload."""
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"Invoking agent for thread: {thread_id}")

    if stream:
        def _stream():
            for output in graph.stream(state, config=config):
                logger.debug(f"Stream event: {list(output.keys())}")
                yield output

        return _stream()

    result = graph.invoke(state, config=config)
    logger.info(f"Agent invocation complete for thread: {thread_id}")
    return result


def initialize_state(thread_id: str, seed_portfolio: dict | None = None) -> PortfolioState:
    """Create initial workflow state for a new thread."""
    seed_portfolio = seed_portfolio or {}
    return {
        "holdings": seed_portfolio,
        "messages": [],
        "current_step": "initialized",
        "total_value": None,
        "currency": "USD",
        "stock_prices": {},
        "pending_trade": None,
        "requires_approval": False,
        "approval_granted": None,
        "thread_id": thread_id,
        "timestamp": datetime.now(),
        "value_history": [],
    }
