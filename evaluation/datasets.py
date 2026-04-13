"""Small local evaluation dataset for the trading agent."""

EVALUATION_CASES = [
    {
        "name": "portfolio_valuation",
        "message": "What is my portfolio worth?",
        "seed_portfolio": {"AAPL": 5, "GOOGL": 2},
        "expected": {
            "requires_approval": False,
            "min_total_value": 1.0,
        },
    },
    {
        "name": "buy_requires_approval",
        "message": "Buy 3 TSLA",
        "seed_portfolio": {},
        "expected": {
            "requires_approval": True,
            "pending_symbol": "TSLA",
        },
    },
    {
        "name": "currency_conversion",
        "message": "Show value in INR",
        "seed_portfolio": {"AAPL": 2},
        "initial_currency": "INR",
        "expected": {
            "requires_approval": False,
        },
    },
]
