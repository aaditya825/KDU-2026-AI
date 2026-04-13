"""Integration tests for the agent graph"""
import pytest
from datetime import datetime
from langchain_core.messages import HumanMessage
from src.agent.graph import initialize_state, create_agent_graph
from src.agent.state import PortfolioState


@pytest.fixture
def agent_graph():
    """Create compiled agent graph for testing"""
    return create_agent_graph()


def test_initialize_state_empty():
    """Test initializing empty portfolio state"""
    state = initialize_state("test-123")

    assert state["thread_id"] == "test-123"
    assert state["holdings"] == {}
    assert state["messages"] == []
    assert state["currency"] == "USD"
    assert state["total_value"] is None


def test_initialize_state_with_seed():
    """Test initializing state with seed portfolio"""
    seed = {"AAPL": 10, "GOOGL": 5}
    state = initialize_state("test-123", seed_portfolio=seed)

    assert state["holdings"] == seed


def test_calculate_portfolio_workflow(agent_graph):
    """Test full workflow: fetch prices -> calculate -> maybe convert"""
    # Start with initial state
    state = initialize_state("test-workflow", seed_portfolio={"AAPL": 10})
    state["messages"] = [HumanMessage(content="How much is my portfolio worth?")]

    # Invoke graph
    config = {"configurable": {"thread_id": "test-workflow"}}
    result = agent_graph.invoke(state, config=config)

    # Should have calculated total value
    assert result.get("total_value") is not None
    assert result.get("total_value") > 0  # AAPL price > 0


def test_buy_trade_workflow_approval_pause(agent_graph):
    """Test buy trade workflow pauses at approval gate"""
    state = initialize_state("test-trade", seed_portfolio={})
    state["messages"] = [HumanMessage(content="Buy 5 AAPL")]

    config = {"configurable": {"thread_id": "test-trade"}}

    # Invoke should pause at approval gate
    result = agent_graph.invoke(state, config=config)

    # Should have pending trade
    assert result.get("pending_trade") is not None
    assert result.get("requires_approval") == True
    assert result.get("pending_trade")["symbol"] == "AAPL"
    assert result.get("pending_trade")["quantity"] == 5


def test_currency_conversion_workflow(agent_graph):
    """Test currency conversion in workflow"""
    state = initialize_state("test-currency", seed_portfolio={"AAPL": 10})
    state["currency"] = "INR"
    state["messages"] = [HumanMessage(content="Show value in INR")]

    config = {"configurable": {"thread_id": "test-currency"}}
    result = agent_graph.invoke(state, config=config)

    # Should be converted to INR (much larger number than USD)
    if result.get("total_value"):
        # INR value should be roughly 83x USD value
        assert result.get("total_value") > 500  # At least 5 AAPL worth
    assert result.get("stock_prices", {}).get("AAPL", 0) > 0


def test_portfolio_persistence_across_invocations(agent_graph):
    """Test that portfolio state persists across invocations via checkpointer"""
    thread_id = "test-persist"
    config = {"configurable": {"thread_id": thread_id}}

    # First invocation: buy AAPL
    state1 = initialize_state(thread_id)
    state1["messages"] = [HumanMessage(content="Buy 5 AAPL")]

    result1 = agent_graph.invoke(state1, config=config)

    # Trade should be pending
    assert result1.get("pending_trade") is not None

    # Simulate approval and second invocation
    state2 = {
        **result1,
        "approval_granted": True,
        "messages": [HumanMessage(content="Approved")],
    }

    result2 = agent_graph.invoke(state2, config=config)

    # AAPL should now be in holdings
    assert result2.get("holdings", {}).get("AAPL", 0) > 0


def test_multiple_trades_sequence(agent_graph):
    """Test sequence of multiple trades"""
    thread_id = "test-multi"
    config = {"configurable": {"thread_id": thread_id}}

    # First trade: buy AAPL
    state1 = initialize_state(thread_id)
    state1["messages"] = [HumanMessage(content="Buy 10 AAPL")]
    result1 = agent_graph.invoke(state1, config=config)

    # Approve
    state2 = {**result1, "approval_granted": True, "messages": []}
    result2 = agent_graph.invoke(state2, config=config)

    # Should have AAPL now
    assert result2["holdings"]["AAPL"] == 10

    # Second trade: buy GOOGL
    state3 = {
        **result2,
        "messages": [HumanMessage(content="Buy 5 GOOGL")],
        "approval_granted": None,  # Reset
        "pending_trade": None,
        "requires_approval": False,
    }
    result3 = agent_graph.invoke(state3, config=config)

    # Should have pending GOOGL trade
    assert result3.get("pending_trade", {}).get("symbol") == "GOOGL"

    # Approve second trade
    state4 = {**result3, "approval_granted": True, "messages": []}
    result4 = agent_graph.invoke(state4, config=config)

    # Should have both AAPL and GOOGL now
    assert result4["holdings"]["AAPL"] == 10
    assert result4["holdings"]["GOOGL"] == 5


def test_sell_trade_workflow(agent_graph):
    """Test sell trade workflow"""
    thread_id = "test-sell"
    config = {"configurable": {"thread_id": thread_id}}

    # Start with AAPL
    state1 = initialize_state(thread_id, seed_portfolio={"AAPL": 10})
    state1["messages"] = [HumanMessage(content="Sell 3 AAPL")]

    result1 = agent_graph.invoke(state1, config=config)

    # Should have pending sell trade
    assert result1.get("pending_trade", {}).get("action") == "sell"
    assert result1.get("pending_trade", {}).get("quantity") == 3

    # Approve
    state2 = {**result1, "approval_granted": True, "messages": []}
    result2 = agent_graph.invoke(state2, config=config)

    # Should have only 7 AAPL left
    assert result2["holdings"]["AAPL"] == 7


def test_error_handling_invalid_symbol(agent_graph):
    """Test error handling for invalid operations"""
    state = initialize_state("test-error")
    state["messages"] = [HumanMessage(content="Buy 1000 INVALID")]

    config = {"configurable": {"thread_id": "test-error"}}

    # Should not crash, but might not execute trade
    result = agent_graph.invoke(state, config=config)

    # Should still return valid state
    assert isinstance(result, dict)
    assert "messages" in result
