# Low Level Design: Stock Trading Agent with LangGraph
## Gemini-Powered Streamlit Application

---

## 1. System Overview

A stateful, multi-step AI agent built using LangGraph and Google Gemini that handles stock trading workflows through an interactive Streamlit web interface. The system supports portfolio management, buy/sell trades with human approval, multi-currency conversion, and comprehensive observability through LangSmith.

### Core Capabilities
- ✅ Conversational portfolio management via Streamlit chat interface
- ✅ Multi-step workflow orchestration with LangGraph
- ✅ User-specific session management with SQLite checkpointing
- ✅ Buy/sell stock trades with mandatory human approval gates
- ✅ Multi-currency support (USD, INR, EUR)
- ✅ Real-time portfolio visualizations (pie charts, value trends)
- ✅ Mock stock price simulation
- ✅ Full LangSmith tracing and evaluation

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Streamlit Web UI                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Single Page Layout                                           │  │
│  │  ┌────────────────┐  ┌──────────────────────────────────┐    │  │
│  │  │  Chat Interface│  │  Portfolio Dashboard             │    │  │
│  │  │  - User input  │  │  - Holdings table                │    │  │
│  │  │  - Agent resp. │  │  - Pie chart (asset allocation)  │    │  │
│  │  │  - Approval UI │  │  - Line chart (value over time)  │    │  │
│  │  └────────────────┘  │  - Total value (multi-currency)  │    │  │
│  │                      └──────────────────────────────────┘    │  │
│  │                                                                │  │
│  │  Session State Management (st.session_state)                  │  │
│  │  - thread_id (user-specific)                                  │  │
│  │  - conversation_history                                       │  │
│  │  - portfolio_data                                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LangGraph Agent Orchestrator                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Portfolio State                            │  │
│  │  - holdings: Dict[str, int]                                   │  │
│  │  - messages: List[BaseMessage]                                │  │
│  │  - stock_prices: Dict[str, float]                             │  │
│  │  - total_value: float                                         │  │
│  │  - currency: str (USD/INR/EUR)                                │  │
│  │  - pending_trade: Optional[Dict]                              │  │
│  │  - approval_granted: Optional[bool]                           │  │
│  │  - thread_id: str                                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Agent Nodes (6 Core)                       │  │
│  │                                                                │  │
│  │  ┌────────────────┐  ┌─────────────────┐  ┌───────────────┐ │  │
│  │  │  1. Analyze    │  │  2. Fetch       │  │  3. Calculate │ │  │
│  │  │     Request    │  │     Stock Price │  │     Portfolio │ │  │
│  │  └────────────────┘  └─────────────────┘  └───────────────┘ │  │
│  │                                                                │  │
│  │  ┌────────────────┐  ┌─────────────────┐  ┌───────────────┐ │  │
│  │  │  4. Currency   │  │  5. Human       │  │  6. Execute   │ │  │
│  │  │     Conversion │  │     Approval    │  │     Trade     │ │  │
│  │  └────────────────┘  └─────────────────┘  └───────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  Conditional Routing                          │  │
│  │  • Currency router (USD → skip, INR/EUR → convert)            │  │
│  │  • Tool router (need prices? → fetch, else → calculate)       │  │
│  │  • Approval router (trade pending? → human gate)              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────┬────────────────────────────────┬─────────────────────┘
             │                                │
             ▼                                ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│  SQLite Checkpointer     │    │   LangSmith Integration         │
│  • Thread-based storage  │    │   • Trace all LLM calls         │
│  • State persistence     │    │   • Track token usage & cost    │
│  • Recovery on reload    │    │   • Custom evaluators           │
│  • File: checkpoints.db  │    │   • Run experiments             │
└──────────────────────────┘    └─────────────────────────────────┘
             │                                │
             └────────────┬───────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       External Dependencies                         │
│                                                                     │
│  ┌─────────────────────┐              ┌─────────────────────────┐  │
│  │  Google Gemini API  │              │  Mock Stock Price API   │  │
│  │  • gemini-1.5-pro   │              │  • Simulated prices     │  │
│  │  • Function calling │              │  • Random fluctuations  │  │
│  └─────────────────────┘              └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Project Folder Structure

```
stock-trading-agent/
│
├── src/
│   ├── __init__.py
│   ├── app.py                       # Streamlit entry point
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py                 # LangGraph definition & compilation
│   │   ├── state.py                 # PortfolioState TypedDict
│   │   ├── nodes.py                 # 6 agent nodes implementation
│   │   └── edges.py                 # Conditional routing functions
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── stock_simulator.py       # Mock stock price generator
│   │   └── currency_converter.py    # USD ↔ INR/EUR conversion
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── components.py            # Reusable Streamlit components
│   │   ├── chat_interface.py        # Chat UI logic
│   │   └── portfolio_viz.py         # Charts & visualizations
│   │
│   ├── checkpointer/
│   │   ├── __init__.py
│   │   └── sqlite_saver.py          # SQLite checkpointer wrapper
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py              # Pydantic settings (API keys, paths)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── session.py               # Streamlit session helpers
│       ├── logger.py                # Logging configuration
│       └── validators.py            # Input validation
│
├── tests/
│   ├── __init__.py
│   ├── test_nodes.py                # Node unit tests
│   ├── test_tools.py                # Tool tests
│   └── test_graph.py                # Integration tests
│
├── evaluation/
│   ├── __init__.py
│   ├── datasets/
│   │   └── eval_cases.json          # Test scenarios
│   └── run_eval.py                  # LangSmith evaluation script
│
├── data/
│   ├── checkpoints.db               # SQLite checkpoint storage
│   └── mock_prices.json             # Initial stock prices
│
├── .streamlit/
│   └── config.toml                  # Streamlit theme config
│
├── requirements.txt
├── .env.example
├── README.md
└── pyproject.toml
```

---

## 4. State Schema

### 4.1 PortfolioState Definition

```python
from typing import TypedDict, Dict, List, Optional, Annotated, Any
from datetime import datetime
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class PortfolioState(TypedDict):
    """
    Central state maintained across the entire workflow.
    Persisted via SQLite checkpointer for cross-session recovery.
    """
    
    # Portfolio holdings: {symbol: quantity}
    holdings: Dict[str, int]
    
    # Conversation history with user
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Current workflow step (for debugging/visualization)
    current_step: str
    
    # Calculated portfolio value
    total_value: Optional[float]
    
    # Target currency for display (USD | INR | EUR)
    currency: str
    
    # Latest fetched stock prices: {symbol: price_usd}
    stock_prices: Dict[str, float]
    
    # Trade awaiting approval: {action: "buy"|"sell", symbol: str, quantity: int}
    pending_trade: Optional[Dict[str, Any]]
    
    # Human approval flag
    requires_approval: bool
    approval_granted: Optional[bool]
    
    # Session identifiers
    thread_id: str
    timestamp: datetime
    
    # Historical portfolio values for time-series chart
    value_history: List[Dict[str, Any]]  # [{timestamp: datetime, value: float}]
```

### 4.2 State Flow Example

```
Initial State (New User)
├─ holdings: {}
├─ messages: []
├─ currency: "USD"
└─ thread_id: "user-abc123"

After "Buy 10 AAPL"
├─ pending_trade: {action: "buy", symbol: "AAPL", quantity: 10}
├─ requires_approval: True
└─ current_step: "human_approval"

After Approval
├─ holdings: {"AAPL": 10}
├─ approval_granted: True
├─ pending_trade: None
└─ value_history: [{timestamp: ..., value: 1755.0}]
```

---

## 5. Agent Nodes Implementation

### Node 1: Analyze Request
**Purpose**: Parse user intent and route to appropriate workflow

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage

def analyze_request(state: PortfolioState) -> PortfolioState:
    """
    Uses Gemini to understand user intent:
    - Calculate portfolio value
    - Buy/sell stocks
    - Change currency
    - View holdings
    
    Updates: current_step, messages
    """
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
    
    # Extract last user message
    user_msg = state["messages"][-1].content
    
    # Gemini analyzes intent
    prompt = f"""
    Analyze this user request: "{user_msg}"
    
    Current portfolio: {state['holdings']}
    Current currency: {state['currency']}
    
    Determine the action needed:
    - "calculate_portfolio": User wants portfolio value
    - "buy_stock": User wants to buy (extract symbol, quantity)
    - "sell_stock": User wants to sell (extract symbol, quantity)
    - "change_currency": User wants different currency (extract target)
    - "view_holdings": User wants to see current stocks
    
    Respond in JSON: {{"action": "...", "params": {{...}}}}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    intent = parse_json(response.content)
    
    state["current_step"] = intent["action"]
    state["messages"].append(AIMessage(content=f"Understood: {intent['action']}"))
    
    # Store trade details if buying/selling
    if intent["action"] in ["buy_stock", "sell_stock"]:
        state["pending_trade"] = {
            "action": intent["action"].replace("_stock", ""),
            "symbol": intent["params"]["symbol"],
            "quantity": intent["params"]["quantity"]
        }
    
    return state
```

---

### Node 2: Fetch Stock Price
**Purpose**: Retrieve mock stock prices for portfolio holdings

```python
from tools.stock_simulator import StockSimulator

def fetch_stock_price(state: PortfolioState) -> PortfolioState:
    """
    Fetches simulated prices for all symbols in holdings.
    Updates: stock_prices
    """
    simulator = StockSimulator()
    
    # Get all unique symbols (holdings + pending trade)
    symbols = set(state["holdings"].keys())
    if state.get("pending_trade"):
        symbols.add(state["pending_trade"]["symbol"])
    
    # Fetch prices
    prices = simulator.get_batch_prices(list(symbols))
    state["stock_prices"] = prices
    
    state["messages"].append(
        AIMessage(content=f"Fetched prices for {len(symbols)} stocks")
    )
    
    return state
```

---

### Node 3: Calculate Portfolio
**Purpose**: Compute total portfolio value in USD

```python
def calculate_portfolio(state: PortfolioState) -> PortfolioState:
    """
    Calculates total value: Σ(quantity × price)
    Updates: total_value
    """
    total = 0.0
    
    for symbol, quantity in state["holdings"].items():
        price = state["stock_prices"].get(symbol, 0.0)
        total += quantity * price
    
    state["total_value"] = total
    state["current_step"] = "calculated"
    
    return state
```

---

### Node 4: Currency Conversion
**Purpose**: Convert USD value to INR or EUR

```python
from tools.currency_converter import CurrencyConverter

def convert_currency(state: PortfolioState) -> PortfolioState:
    """
    Converts total_value from USD to target currency.
    Only runs if currency != "USD"
    Updates: total_value (converted)
    """
    if state["currency"] == "USD":
        return state
    
    converter = CurrencyConverter()
    converted = converter.convert(
        amount=state["total_value"],
        from_currency="USD",
        to_currency=state["currency"]
    )
    
    state["total_value"] = converted
    state["messages"].append(
        AIMessage(content=f"Converted to {state['currency']}")
    )
    
    return state
```

---

### Node 5: Human Approval Gate
**Purpose**: Pause execution for user confirmation on trades

```python
def human_approval_gate(state: PortfolioState) -> PortfolioState:
    """
    Sets requires_approval flag and pauses graph.
    Streamlit UI will detect this and show approval buttons.
    Updates: requires_approval
    """
    trade = state["pending_trade"]
    
    state["requires_approval"] = True
    state["messages"].append(
        AIMessage(
            content=f"⚠️ Approval Required:\n"
                    f"{trade['action'].upper()} {trade['quantity']} shares of {trade['symbol']}\n"
                    f"Estimated cost: ${state['stock_prices'][trade['symbol']] * trade['quantity']:.2f}"
        )
    )
    
    # Graph will interrupt here (configured in compile())
    return state
```

---

### Node 6: Execute Trade
**Purpose**: Perform approved buy/sell transaction

```python
def execute_trade(state: PortfolioState) -> PortfolioState:
    """
    Executes trade only if approval_granted = True.
    Updates: holdings, value_history, messages
    """
    if not state.get("approval_granted"):
        state["messages"].append(AIMessage(content="Trade cancelled by user"))
        state["pending_trade"] = None
        return state
    
    trade = state["pending_trade"]
    symbol = trade["symbol"]
    quantity = trade["quantity"]
    action = trade["action"]
    
    # Update holdings
    current_qty = state["holdings"].get(symbol, 0)
    
    if action == "buy":
        state["holdings"][symbol] = current_qty + quantity
    elif action == "sell":
        new_qty = current_qty - quantity
        if new_qty > 0:
            state["holdings"][symbol] = new_qty
        else:
            del state["holdings"][symbol]
    
    # Record value snapshot
    state["value_history"].append({
        "timestamp": datetime.now(),
        "value": state.get("total_value", 0.0),
        "action": f"{action} {quantity} {symbol}"
    })
    
    state["messages"].append(
        AIMessage(content=f"✅ Trade executed: {action} {quantity} {symbol}")
    )
    
    # Clear trade state
    state["pending_trade"] = None
    state["requires_approval"] = False
    state["approval_granted"] = None
    
    return state
```

---

## 6. Conditional Routing Logic

### 6.1 Currency Router
```python
def should_convert_currency(state: PortfolioState) -> str:
    """
    Decides if currency conversion is needed.
    Returns: "convert_currency" | "respond"
    """
    if state["currency"] in ["INR", "EUR"]:
        return "convert_currency"
    return "respond"
```

### 6.2 Tool Router
```python
def needs_stock_price(state: PortfolioState) -> str:
    """
    Checks if stock prices need to be fetched.
    Returns: "fetch_prices" | "calculate"
    """
    # Need prices if we're calculating and don't have them
    if state["current_step"] == "calculate_portfolio":
        if not state.get("stock_prices") or len(state["stock_prices"]) == 0:
            return "fetch_prices"
    return "calculate"
```

### 6.3 Approval Router
```python
def needs_approval(state: PortfolioState) -> str:
    """
    Routes trades through human approval gate.
    Returns: "human_approval" | "execute_trade"
    """
    if state.get("pending_trade") and not state.get("approval_granted"):
        return "human_approval"
    return "execute_trade"
```

---

## 7. LangGraph Definition

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

def create_agent_graph():
    """
    Builds and compiles the LangGraph agent.
    Returns: Compiled graph with checkpointer
    """
    
    # Initialize graph
    workflow = StateGraph(PortfolioState)
    
    # Add all 6 nodes
    workflow.add_node("analyze", analyze_request)
    workflow.add_node("fetch_prices", fetch_stock_price)
    workflow.add_node("calculate", calculate_portfolio)
    workflow.add_node("convert_currency", convert_currency)
    workflow.add_node("human_approval", human_approval_gate)
    workflow.add_node("execute_trade", execute_trade)
    
    # Set entry point
    workflow.set_entry_point("analyze")
    
    # Define edges
    workflow.add_conditional_edges(
        "analyze",
        needs_stock_price,
        {
            "fetch_prices": "fetch_prices",
            "calculate": "calculate"
        }
    )
    
    workflow.add_edge("fetch_prices", "calculate")
    
    workflow.add_conditional_edges(
        "calculate",
        should_convert_currency,
        {
            "convert_currency": "convert_currency",
            "respond": END
        }
    )
    
    workflow.add_edge("convert_currency", END)
    
    workflow.add_conditional_edges(
        "human_approval",
        needs_approval,
        {
            "execute_trade": "execute_trade"
        }
    )
    
    workflow.add_edge("execute_trade", END)
    
    # Compile with SQLite checkpointer
    checkpointer = SqliteSaver.from_conn_string("data/checkpoints.db")
    
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval"]  # Pause for approval
    )
    
    return app
```

---

## 8. Tools Implementation

### 8.1 Mock Stock Price Simulator

```python
import random
from typing import Dict, List

class StockSimulator:
    """Generates realistic mock stock prices with random fluctuations"""
    
    # Base prices (USD)
    BASE_PRICES = {
        "AAPL": 175.50,
        "GOOGL": 140.25,
        "MSFT": 380.00,
        "TSLA": 245.30,
        "AMZN": 178.90,
        "META": 485.20,
        "NVDA": 875.40,
        "NFLX": 625.10
    }
    
    def get_price(self, symbol: str) -> float:
        """
        Get current price with ±3% random fluctuation.
        Simulates market volatility.
        """
        base = self.BASE_PRICES.get(symbol, 100.0)
        fluctuation = random.uniform(-0.03, 0.03)
        return round(base * (1 + fluctuation), 2)
    
    def get_batch_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Fetch multiple prices at once"""
        return {symbol: self.get_price(symbol) for symbol in symbols}
    
    def add_symbol(self, symbol: str, price: float):
        """Add new stock to simulator"""
        self.BASE_PRICES[symbol] = price
```

### 8.2 Currency Converter

```python
class CurrencyConverter:
    """Convert between USD, INR, and EUR"""
    
    # Exchange rates (relative to USD)
    RATES = {
        "USD": 1.0,
        "INR": 83.12,   # 1 USD = 83.12 INR
        "EUR": 0.92     # 1 USD = 0.92 EUR
    }
    
    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        """
        Convert amount from one currency to another.
        Always converts through USD as intermediate.
        """
        # Convert to USD first
        usd_amount = amount / self.RATES[from_currency]
        
        # Convert from USD to target
        result = usd_amount * self.RATES[to_currency]
        
        return round(result, 2)
    
    def get_symbol(self, currency: str) -> str:
        """Get currency symbol for display"""
        symbols = {"USD": "$", "INR": "₹", "EUR": "€"}
        return symbols.get(currency, "$")
```

---

## 9. Streamlit UI Implementation

### 9.1 Main App Layout (app.py)

```python
import streamlit as st
from src.agent.graph import create_agent_graph
from src.ui.chat_interface import render_chat
from src.ui.portfolio_viz import render_portfolio_dashboard
from src.utils.session import init_session_state

# Page config
st.set_page_config(
    page_title="Stock Trading Agent",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
init_session_state()

# Header
st.title("📈 AI Stock Trading Agent")
st.caption("Powered by LangGraph & Google Gemini")

# Two-column layout
col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("💬 Chat")
    render_chat()

with col2:
    st.subheader("📊 Portfolio Dashboard")
    render_portfolio_dashboard()
```

### 9.2 Chat Interface Component

```python
# src/ui/chat_interface.py

import streamlit as st
from langchain_core.messages import HumanMessage

def render_chat():
    """Renders chat interface with message history and input"""
    
    # Display message history
    for msg in st.session_state.messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.write(msg.content)
    
    # User input
    if prompt := st.chat_input("Ask about your portfolio or trade stocks..."):
        # Add user message
        st.session_state.messages.append(HumanMessage(content=prompt))
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Invoke agent
        with st.spinner("Thinking..."):
            agent = create_agent_graph()
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            
            state = {
                "messages": st.session_state.messages,
                "holdings": st.session_state.portfolio,
                "currency": st.session_state.currency,
                "thread_id": st.session_state.thread_id
            }
            
            result = agent.invoke(state, config=config)
            
            # Check if approval needed
            if result.get("requires_approval"):
                st.session_state.pending_trade = result["pending_trade"]
                render_approval_ui()
            else:
                # Update session
                st.session_state.messages = result["messages"]
                st.session_state.portfolio = result["holdings"]
                
                # Display response
                with st.chat_message("assistant"):
                    st.write(result["messages"][-1].content)

def render_approval_ui():
    """Shows approval/reject buttons for trades"""
    st.warning("⚠️ Trade approval required")
    
    trade = st.session_state.pending_trade
    st.info(f"{trade['action'].upper()} {trade['quantity']} {trade['symbol']}")
    
    col1, col2 = st.columns(2)
    
    if col1.button("✅ Approve", type="primary"):
        # Update state and resume graph
        approve_trade()
    
    if col2.button("❌ Reject", type="secondary"):
        reject_trade()
```

### 9.3 Portfolio Visualization Component

```python
# src/ui/portfolio_viz.py

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def render_portfolio_dashboard():
    """Renders portfolio visualizations"""
    
    portfolio = st.session_state.portfolio
    prices = st.session_state.stock_prices
    currency = st.session_state.currency
    
    if not portfolio:
        st.info("No holdings yet. Start by buying some stocks!")
        return
    
    # Calculate values
    holdings_data = []
    for symbol, quantity in portfolio.items():
        price = prices.get(symbol, 0)
        value = quantity * price
        holdings_data.append({
            "Symbol": symbol,
            "Quantity": quantity,
            "Price": f"${price:.2f}",
            "Value": value
        })
    
    df = pd.DataFrame(holdings_data)
    total_value = df["Value"].sum()
    
    # Convert to selected currency
    if currency != "USD":
        converter = CurrencyConverter()
        total_value = converter.convert(total_value, "USD", currency)
    
    # Display total
    symbol = CurrencyConverter().get_symbol(currency)
    st.metric("Total Portfolio Value", f"{symbol}{total_value:,.2f}")
    
    # Holdings table
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Pie chart - Asset Allocation
    fig_pie = px.pie(
        df,
        values="Value",
        names="Symbol",
        title="Asset Allocation",
        hole=0.4
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Line chart - Portfolio Value Over Time
    if st.session_state.value_history:
        history_df = pd.DataFrame(st.session_state.value_history)
        
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=history_df["timestamp"],
            y=history_df["value"],
            mode="lines+markers",
            name="Portfolio Value",
            line=dict(color="#1f77b4", width=2)
        ))
        
        fig_line.update_layout(
            title="Portfolio Value Over Time",
            xaxis_title="Date",
            yaxis_title=f"Value ({currency})",
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_line, use_container_width=True)
```

---

## 10. Session Management

### 10.1 Streamlit Session Initialization

```python
# src/utils/session.py

import streamlit as st
import uuid
from datetime import datetime

def init_session_state():
    """Initialize Streamlit session state with defaults"""
    
    if "initialized" not in st.session_state:
        # Generate unique thread ID per user session
        st.session_state.thread_id = f"user-{uuid.uuid4().hex[:8]}"
        
        # Portfolio data
        st.session_state.portfolio = {}  # {symbol: quantity}
        st.session_state.stock_prices = {}
        st.session_state.currency = "USD"
        
        # Conversation
        st.session_state.messages = []
        
        # Trade management
        st.session_state.pending_trade = None
        
        # History tracking
        st.session_state.value_history = []
        
        # Flag
        st.session_state.initialized = True

def get_thread_config():
    """Returns LangGraph config with current thread_id"""
    return {"configurable": {"thread_id": st.session_state.thread_id}}
```

### 10.2 Multi-User Session Isolation

Each Streamlit user gets:
- **Unique `thread_id`**: Generated on first visit
- **Isolated checkpoint**: SQLite stores state per thread
- **Separate portfolio**: No cross-contamination between users
- **Independent chat history**: Messages scoped to session

---

## 11. LangSmith Integration

### 11.1 Configuration

```python
# src/config/settings.py

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    google_api_key: str
    langsmith_api_key: str
    
    # LangSmith Config
    langsmith_project: str = "stock-trading-agent"
    langchain_tracing_v2: bool = True
    langchain_endpoint: str = "https://api.smith.langchain.com"
    
    # App Config
    database_path: str = "data/checkpoints.db"
    
    class Config:
        env_file = ".env"

settings = Settings()

# Set environment variables for LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langchain_tracing_v2)
os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
```

### 11.2 Tracked Metrics

**Automatic Tracking:**
- ✅ All LLM calls (Gemini invocations)
- ✅ Input/output tokens per request
- ✅ Latency per node
- ✅ Total cost (based on Gemini pricing)
- ✅ Graph execution path
- ✅ State transitions

**Custom Metadata:**
```python
from langsmith import traceable

@traceable(
    run_type="tool",
    name="fetch_stock_price",
    metadata={"tool_type": "stock_api", "cache_enabled": False}
)
def fetch_stock_price(state: PortfolioState) -> PortfolioState:
    # Implementation
    pass
```

### 11.3 Cost Tracking Example

```python
# Gemini Pricing (as of 2024)
# gemini-1.5-pro: $0.00125 / 1K input tokens, $0.005 / 1K output tokens

# LangSmith automatically calculates cost per trace
# View in dashboard: https://smith.langchain.com
```

---

## 12. Evaluation Strategy

### 12.1 Test Dataset Structure

```json
{
  "test_cases": [
    {
      "id": "calc_portfolio_usd",
      "input": {
        "holdings": {"AAPL": 10, "GOOGL": 5},
        "currency": "USD",
        "user_message": "What's my portfolio worth?"
      },
      "expected": {
        "has_total_value": true,
        "currency": "USD",
        "nodes_executed": ["analyze", "fetch_prices", "calculate"]
      }
    },
    {
      "id": "buy_with_approval",
      "input": {
        "holdings": {},
        "user_message": "Buy 5 shares of TSLA"
      },
      "expected": {
        "pending_trade": {"action": "buy", "symbol": "TSLA", "quantity": 5},
        "requires_approval": true,
        "nodes_executed": ["analyze", "human_approval"]
      }
    },
    {
      "id": "currency_conversion_inr",
      "input": {
        "holdings": {"MSFT": 3},
        "currency": "INR",
        "user_message": "Show value in rupees"
      },
      "expected": {
        "has_total_value": true,
        "currency": "INR",
        "nodes_executed": ["analyze", "fetch_prices", "calculate", "convert_currency"]
      }
    }
  ]
}
```

### 12.2 Evaluation Script

```python
# evaluation/run_eval.py

from langsmith.evaluation import evaluate
from langsmith.schemas import Run, Example
from src.agent.graph import create_agent_graph

def accuracy_evaluator(run: Run, example: Example) -> dict:
    """Check if agent produced correct output"""
    outputs = run.outputs
    expected = example.outputs
    
    # Check total_value exists
    if expected.get("has_total_value"):
        score = 1.0 if outputs.get("total_value") is not None else 0.0
    
    # Check currency matches
    if expected.get("currency"):
        score = 1.0 if outputs.get("currency") == expected["currency"] else 0.0
    
    return {"key": "accuracy", "score": score}

def routing_evaluator(run: Run, example: Example) -> dict:
    """Check if correct nodes were executed"""
    expected_nodes = example.outputs.get("nodes_executed", [])
    
    # Extract actual nodes from trace (would need to parse run metadata)
    # For now, simplified check
    score = 1.0  # Placeholder
    
    return {"key": "routing_accuracy", "score": score}

# Run evaluation
agent = create_agent_graph()

results = evaluate(
    lambda inputs: agent.invoke(inputs),
    data="stock-trading-eval-dataset",
    evaluators=[accuracy_evaluator, routing_evaluator],
    experiment_prefix="portfolio-agent-v1"
)

print(results)
```

### 12.3 Evaluation Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Accuracy** | Correct portfolio calculations | > 95% |
| **Routing Accuracy** | Correct node path selection | > 90% |
| **Approval Detection** | Correctly triggers human gate | 100% |
| **Latency** | End-to-end response time | < 3s |
| **Token Efficiency** | Tokens per interaction | < 2000 |

---

## 13. Error Handling

### 13.1 Node-Level Error Handling

```python
def fetch_stock_price(state: PortfolioState) -> PortfolioState:
    """Fetch prices with fallback on failure"""
    try:
        simulator = StockSimulator()
        prices = simulator.get_batch_prices(list(state["holdings"].keys()))
        state["stock_prices"] = prices
        
    except Exception as e:
        logger.error(f"Stock price fetch failed: {e}")
        
        # Fallback: use last known prices or defaults
        state["stock_prices"] = state.get("stock_prices", {})
        state["messages"].append(
            AIMessage(content="⚠️ Using cached prices (live data unavailable)")
        )
    
    return state
```

### 13.2 Streamlit Error Display

```python
try:
    result = agent.invoke(state, config=config)
except Exception as e:
    st.error(f"Agent error: {str(e)}")
    logger.exception("Agent invocation failed")
    
    # Optionally: rollback to last checkpoint
    st.info("Recovering from last saved state...")
```

---

## 14. Testing Strategy

### 14.1 Unit Tests (Minimal Examples)

```python
# tests/test_nodes.py

import pytest
from src.agent.nodes import calculate_portfolio

def test_calculate_portfolio_basic():
    """Test portfolio calculation with known prices"""
    state = {
        "holdings": {"AAPL": 10, "GOOGL": 5},
        "stock_prices": {"AAPL": 175.00, "GOOGL": 140.00},
        "currency": "USD"
    }
    
    result = calculate_portfolio(state)
    
    expected_value = (10 * 175.00) + (5 * 140.00)  # 2450.0
    assert abs(result["total_value"] - expected_value) < 0.01

def test_calculate_portfolio_empty():
    """Test with empty portfolio"""
    state = {"holdings": {}, "stock_prices": {}}
    
    result = calculate_portfolio(state)
    
    assert result["total_value"] == 0.0
```

### 14.2 Integration Test Example

```python
# tests/test_graph.py

def test_full_workflow_buy_stock():
    """Test complete buy workflow with approval"""
    
    agent = create_agent_graph()
    config = {"configurable": {"thread_id": "test-123"}}
    
    # Step 1: User requests buy
    initial_state = {
        "messages": [HumanMessage(content="Buy 10 AAPL")],
        "holdings": {},
        "thread_id": "test-123"
    }
    
    result = agent.invoke(initial_state, config=config)
    
    # Should pause at approval gate
    assert result["requires_approval"] == True
    assert result["pending_trade"]["symbol"] == "AAPL"
    
    # Step 2: Approve trade
    approval_state = {**result, "approval_granted": True}
    final_result = agent.invoke(approval_state, config=config)
    
    # Should have updated holdings
    assert final_result["holdings"]["AAPL"] == 10
```

---

## 15. Deployment Configuration

### 15.1 Environment Variables (.env)

```bash
# Google Gemini
GOOGLE_API_KEY=AIzaSy...

# LangSmith
LANGSMITH_API_KEY=lsv2_pt_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=stock-trading-agent

# App Config
DATABASE_PATH=data/checkpoints.db
```

### 15.2 Requirements

```txt
# Core Dependencies
streamlit==1.32.0
langgraph==0.2.0
langchain==0.3.0
langchain-google-genai==2.0.0
langsmith==0.2.0

# Data & Visualization
pandas==2.2.0
plotly==5.18.0

# Config & Utilities
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0

# Testing
pytest==7.4.0
pytest-asyncio==0.23.0
```

### 15.3 Streamlit Config (.streamlit/config.toml)

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[server]
port = 8501
enableCORS = false
enableXsrfProtection = true
```

---

## 16. Key Workflows

### 16.1 Calculate Portfolio Value

```
User: "What's my portfolio worth in EUR?"
  ↓
1. analyze_request → current_step = "calculate_portfolio", currency = "EUR"
  ↓
2. needs_stock_price → "fetch_prices" (no prices cached)
  ↓
3. fetch_stock_price → stock_prices = {AAPL: 175.50, ...}
  ↓
4. calculate_portfolio → total_value = 2450.0 USD
  ↓
5. should_convert_currency → "convert_currency" (EUR requested)
  ↓
6. convert_currency → total_value = 2254.0 EUR
  ↓
7. END → Return response to user
```

### 16.2 Buy Stock with Approval

```
User: "Buy 5 TSLA"
  ↓
1. analyze_request → pending_trade = {action: "buy", symbol: "TSLA", quantity: 5}
  ↓
2. needs_approval → "human_approval"
  ↓
3. human_approval_gate → requires_approval = True, PAUSE
  ↓
[Streamlit shows approval UI]
  ↓
User clicks "Approve"
  ↓
4. Graph resumed with approval_granted = True
  ↓
5. execute_trade → holdings["TSLA"] = 5, record in value_history
  ↓
6. END → Confirmation message
```

---

## 17. Performance Optimizations

### 17.1 Caching Strategy

```python
import streamlit as st
from functools import lru_cache

@st.cache_resource
def get_agent():
    """Cache compiled agent graph"""
    return create_agent_graph()

@lru_cache(maxsize=128)
def get_stock_price(symbol: str, cache_key: int):
    """Cache stock prices for 5 minutes (cache_key changes every 5 min)"""
    return StockSimulator().get_price(symbol)

# Usage in Streamlit
cache_key = int(time.time() / 300)  # Changes every 5 minutes
price = get_stock_price("AAPL", cache_key)
```

### 17.2 Async Price Fetching (Future Enhancement)

```python
import asyncio

async def fetch_prices_async(symbols: List[str]) -> Dict[str, float]:
    """Fetch multiple prices concurrently"""
    tasks = [get_price_async(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks)
    return dict(zip(symbols, results))
```

---

## 18. Security Considerations

1. **API Key Protection**: Use `.env` file, never commit to git
2. **Input Sanitization**: Validate stock symbols (alphanumeric only)
3. **Trade Limits**: Enforce max quantity per trade (e.g., 1000 shares)
4. **Session Isolation**: Thread-based checkpointing prevents cross-user data leaks
5. **Approval Audit**: Log all human approvals with timestamp

---

## 19. Monitoring & Observability

### 19.1 Key Metrics to Track

- **User Activity**: Sessions per day, messages per session
- **Agent Performance**: Average latency, error rate
- **Portfolio Metrics**: Total value managed, trades executed
- **LangSmith Metrics**: Token usage, cost per user

### 19.2 Logging Configuration

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agent.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

---

## 20. Future Enhancements

1. **Real Stock API Integration**: Replace mock with Alpha Vantage / Polygon.io
2. **Portfolio Optimization**: AI-suggested rebalancing strategies
3. **Historical Backtesting**: Simulate past performance
4. **Multi-Asset Support**: Add crypto, commodities
5. **Mobile Responsive UI**: Optimize for mobile browsers
6. **Voice Interface**: Speech-to-text for hands-free trading
7. **Automated Trading Rules**: Set buy/sell triggers

---

## Appendix A: Sample Interactions

### Interaction 1: First-Time User

```
User: "Hello"
Agent: "Hi! I'm your AI trading assistant. I can help you:
        - View your portfolio
        - Buy/sell stocks
        - Calculate portfolio value in different currencies
        What would you like to do?"

User: "Buy 10 shares of Apple"
Agent: "⚠️ Approval Required:
        BUY 10 shares of AAPL
        Estimated cost: $1,755.00
        [Approve] [Reject]"

[User clicks Approve]

Agent: "✅ Trade executed: buy 10 AAPL
        Your portfolio now has 10 shares of AAPL worth $1,755.00"
```

### Interaction 2: Portfolio Inquiry

```
User: "Show my portfolio value in Indian rupees"
Agent: "Fetching latest prices...
        
        Your Portfolio (INR):
        - AAPL: 10 shares @ ₹14,587.20 = ₹145,872.00
        - GOOGL: 5 shares @ ₹11,660.76 = ₹58,303.80
        
        Total: ₹204,175.80"
```

---

## Appendix B: Troubleshooting

### Issue: "Graph stuck at human_approval"

**Solution**: Ensure `approval_granted` is set in state before resuming graph.

### Issue: "Stock prices not updating"

**Solution**: Clear `stock_prices` cache or reduce cache TTL.

### Issue: "LangSmith traces not appearing"

**Solution**: Verify `LANGCHAIN_TRACING_V2=true` and API key is correct.

---

*Document Version: 2.0 (Gemini + Streamlit Edition)*  
*Last Updated: 2026-04-13*  
*Tailored for: Moderate complexity, user sessions, full observability*
