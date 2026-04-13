"""Unit tests for agent nodes"""
import pytest
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from src.agent.state import PortfolioState
from src.agent.nodes import (
    calculate_portfolio,
    convert_currency,
    execute_trade,
)


# Test fixtures
@pytest.fixture
def basic_state() -> PortfolioState:
    """Create a basic test state"""
    return {
        "holdings": {"AAPL": 10, "GOOGL": 5},
        "messages": [HumanMessage(content="Test")],
        "current_step": "testing",
        "total_value": None,
        "currency": "USD",
        "stock_prices": {"AAPL": 175.00, "GOOGL": 140.00},
        "pending_trade": None,
        "requires_approval": False,
        "approval_granted": None,
        "thread_id": "test-123",
        "timestamp": datetime.now(),
        "value_history": [],
    }


# Tests for calculate_portfolio node
def test_calculate_portfolio_basic(basic_state):
    """Test portfolio calculation with known prices"""
    result = calculate_portfolio(basic_state)

    expected_value = (10 * 175.00) + (5 * 140.00)  # 2450.0
    assert abs(result["total_value"] - expected_value) < 0.01
    assert result["total_value"] == 2450.0
    assert "portfolio value" in str(result["messages"][-1].content).lower()


def test_calculate_portfolio_empty():
    """Test with empty portfolio"""
    state = {
        "holdings": {},
        "messages": [],
        "current_step": "",
        "total_value": None,
        "currency": "USD",
        "stock_prices": {},
        "pending_trade": None,
        "requires_approval": False,
        "approval_granted": None,
        "thread_id": "test",
        "timestamp": datetime.now(),
        "value_history": [],
    }

    result = calculate_portfolio(state)
    assert result["total_value"] == 0.0


def test_calculate_portfolio_partial_prices(basic_state):
    """Test calculation when not all prices are available"""
    basic_state["stock_prices"] = {"AAPL": 175.00}  # Missing GOOGL

    result = calculate_portfolio(basic_state)

    expected_value = (10 * 175.00) + (5 * 0.00)  # 1750.0
    assert result["total_value"] == 1750.0


# Tests for convert_currency node
def test_convert_currency_usd_to_inr(basic_state):
    """Test USD to INR conversion"""
    basic_state["total_value"] = 1000.0
    basic_state["currency"] = "INR"

    result = convert_currency(basic_state)

    # 1000 USD * 83.12 = 83120 INR
    expected = 83120.0
    assert abs(result["total_value"] - expected) < 0.1


def test_convert_currency_usd_to_eur(basic_state):
    """Test USD to EUR conversion"""
    basic_state["total_value"] = 1000.0
    basic_state["currency"] = "EUR"

    result = convert_currency(basic_state)

    # 1000 USD * 0.92 = 920 EUR
    expected = 920.0
    assert abs(result["total_value"] - expected) < 0.1


def test_convert_currency_no_conversion_needed(basic_state):
    """Test that USD to USD doesn't change value"""
    basic_state["total_value"] = 2450.0
    basic_state["currency"] = "USD"

    result = convert_currency(basic_state)

    assert result["total_value"] == 2450.0


# Tests for execute_trade node
def test_execute_trade_buy_approved(basic_state):
    """Test executing an approved buy trade"""
    basic_state["pending_trade"] = {
        "action": "buy",
        "symbol": "TSLA",
        "quantity": 3,
    }
    basic_state["approval_granted"] = True
    basic_state["stock_prices"]["TSLA"] = 245.30

    result = execute_trade(basic_state)

    assert result["holdings"]["TSLA"] == 3
    assert result["total_value"] == (10 * 175.00) + (5 * 140.00) + (3 * 245.30)
    assert result["pending_trade"] is None
    assert result["approval_granted"] is None


def test_execute_trade_buy_adds_to_existing(basic_state):
    """Test buying more of an existing holding"""
    basic_state["holdings"]["AAPL"] = 10
    basic_state["pending_trade"] = {
        "action": "buy",
        "symbol": "AAPL",
        "quantity": 5,
    }
    basic_state["approval_granted"] = True

    result = execute_trade(basic_state)

    assert result["holdings"]["AAPL"] == 15


def test_execute_trade_sell_approved(basic_state):
    """Test executing an approved sell trade"""
    basic_state["holdings"]["AAPL"] = 10
    basic_state["pending_trade"] = {
        "action": "sell",
        "symbol": "AAPL",
        "quantity": 3,
    }
    basic_state["approval_granted"] = True

    result = execute_trade(basic_state)

    assert result["holdings"]["AAPL"] == 7


def test_execute_trade_sell_all(basic_state):
    """Test selling all shares of a stock"""
    basic_state["holdings"]["AAPL"] = 10
    basic_state["pending_trade"] = {
        "action": "sell",
        "symbol": "AAPL",
        "quantity": 10,
    }
    basic_state["approval_granted"] = True

    result = execute_trade(basic_state)

    assert "AAPL" not in result["holdings"]


def test_execute_trade_sell_insufficient_shares(basic_state):
    """Test selling more shares than available"""
    basic_state["holdings"]["AAPL"] = 5
    basic_state["pending_trade"] = {
        "action": "sell",
        "symbol": "AAPL",
        "quantity": 10,
    }
    basic_state["approval_granted"] = True

    result = execute_trade(basic_state)

    # Should not execute - holdings unchanged
    assert result["holdings"]["AAPL"] == 5


def test_execute_trade_rejected(basic_state):
    """Test rejecting a trade"""
    basic_state["pending_trade"] = {
        "action": "buy",
        "symbol": "TSLA",
        "quantity": 3,
    }
    basic_state["approval_granted"] = False

    result = execute_trade(basic_state)

    assert result["pending_trade"] is None
    assert "TSLA" not in result.get("holdings", {})


def test_execute_trade_updates_value_history(basic_state):
    """Test that trade execution records in value history"""
    basic_state["total_value"] = 2450.0
    basic_state["pending_trade"] = {
        "action": "buy",
        "symbol": "TSLA",
        "quantity": 3,
    }
    basic_state["approval_granted"] = True
    basic_state["value_history"] = []

    result = execute_trade(basic_state)

    assert len(result["value_history"]) == 1
    assert result["value_history"][0]["action"] == "buy 3 TSLA"
    assert result["value_history"][0]["value"] == 2450.0
