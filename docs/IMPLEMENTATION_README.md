# 📈 AI Stock Trading Agent

A stateful, multi-step AI agent built with **LangGraph** and **Google Gemini** that handles stock trading workflows through an interactive **Streamlit** web interface.

## 🌟 Features

✅ **Conversational Portfolio Management** - Chat interface for trading  
✅ **Multi-Step LLM Orchestration** - 6-node LangGraph workflow  
✅ **User Session Management** - SQLite checkpointing for state persistence  
✅ **Buy/Sell Trades** - Mandatory human approval gates  
✅ **Multi-Currency Support** - USD, INR, EUR conversion  
✅ **Real-Time Visualizations** - Pie charts, line charts, portfolio metrics  
✅ **Mock Stock Prices** - Configurable simulated market  
✅ **Full LangSmith Integration** - Complete observability & tracing  

## 🏗️ Architecture

```
Streamlit UI
    ↓
Chat Interface ←→ Portfolio Dashboard
    ↓
LangGraph Agent (6 Nodes)
    ├─ Analyze Request
    ├─ Fetch Stock Price
    ├─ Calculate Portfolio
    ├─ Currency Conversion
    ├─ Human Approval Gate
    └─ Execute Trade
    ↓
SQLite Checkpointer (State Persistence)
```

### Agent Workflow

1. **Analyze Request** - Gemini analyzes user intent (buy/sell/calculate/convert)
2. **Fetch Prices** - Mock stock prices fetched (conditional)
3. **Calculate Portfolio** - Total value computed
4. **Currency Conversion** - Convert USD to target currency (conditional)
5. **Human Approval** - Trades pause for user confirmation (interrupt)
6. **Execute Trade** - Approved trades executed, holdings updated

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Google Gemini API Key
- LangSmith API Key (optional, for observability)

### Installation

1. **Clone & Setup**

```bash
cd KDU-2026-AI
python -m venv venv
.\venv\Scripts\Activate.ps1  # PowerShell
# or
source venv/bin/activate     # macOS/Linux
```

2. **Install Dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure Environment**

```bash
cp .env.example .env
# Edit .env and add your API keys
```

4. **Run Application**

```bash
streamlit run src/app.py
```

Open http://localhost:8501 in browser.

## 📁 Project Structure

```
stock-trading-agent/
├── src/
│   ├── agent/
│   │   ├── state.py          # PortfolioState TypedDict
│   │   ├── nodes.py          # 6 agent nodes
│   │   ├── edges.py          # Routing logic
│   │   └── graph.py          # LangGraph compilation
│   ├── tools/
│   │   ├── stock_simulator.py    # Mock prices
│   │   └── currency_converter.py # USD ↔ INR/EUR
│   ├── ui/
│   │   ├── components.py      # Reusable UI elements
│   │   ├── chat_interface.py  # Chat UI
│   │   └── portfolio_viz.py   # Visualizations
│   ├── config/
│   │   └── settings.py        # Configuration
│   ├── utils/
│   │   ├── session.py         # Session management
│   │   └── logger.py          # Logging setup
│   └── app.py                 # Streamlit entry point
├── tests/
│   ├── test_nodes.py          # Unit tests
│   └── test_graph.py          # Integration tests
├── data/
│   └── checkpoints.db         # SQLite state store
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## 🎮 Usage Examples

### Chat Commands

```
"Buy 10 AAPL"
"Sell 5 GOOGL"
"What's my portfolio worth?"
"Show value in INR"
"View my holdings"
```

### User Interaction Flow

```
1. User: "Buy 10 AAPL"
   ↓
2. Agent analyzes intent, fetches price
   ↓
3. ⚠️ Approval Required modal appears
   Symbol: AAPL, Quantity: 10, Cost: $1,755.00
   ↓
4. User clicks [Approve]
   ↓
5. Agent executes trade
   ✅ Trade executed: buy 10 AAPL
   ↓
6. Portfolio updated and visualized
```

## 🔧 Configuration

### .env Variables

```bash
# Google Gemini
GOOGLE_API_KEY=AIzaSy...

# LangSmith (optional)
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=stock-trading-agent
LANGCHAIN_TRACING_V2=true

# App
DATABASE_PATH=data/checkpoints.db
DEBUG=false
LOG_LEVEL=INFO
```

### Stock Symbols

Default supported symbols (easily expandable):
- AAPL, GOOGL, MSFT, TSLA, AMZN, META, NVDA, NFLX

Add more:
```python
from src.tools.stock_simulator import get_simulator
simulator = get_simulator()
simulator.add_symbol("NEW_SYMBOL", 100.0)
```

### Currency Support

- USD (US Dollar) - `$`
- INR (Indian Rupee) - `₹`
- EUR (Euro) - `€`

Exchange rates in `src/tools/currency_converter.py`

## 🧪 Testing

### Run Unit Tests

```bash
pytest tests/test_nodes.py -v
```

### Run Integration Tests

```bash
pytest tests/test_graph.py -v
```

### Run All Tests

```bash
pytest tests/ -v --tb=short
```

### Test Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

## 📊 LangSmith Integration

### Enable Tracing

1. Set `LANGCHAIN_TRACING_V2=true` in `.env`
2. Add valid `LANGSMITH_API_KEY`
3. Invoke agent - all LLM calls auto-traced

### View Traces

Dashboard: https://smith.langchain.com/projects/stock-trading-agent

Metrics tracked:
- ✅ LLM invocations
- ✅ Token usage (input/output)
- ✅ Latency per node
- ✅ Total cost (Gemini pricing)
- ✅ Execution paths
- ✅ State transitions

## 📈 State Persistence

### SQLite Checkpoints

- **Location**: `data/checkpoints.db`
- **Per User**: Separate checkpoint per `thread_id`
- **Resumable**: Recover from interrupts automatically
- **Query** checkpoints:

```bash
sqlite3 data/checkpoints.db "SELECT * FROM checkpoint_writes LIMIT 5;"
```

## 🔍 Monitoring & Logging

### Log Files

- **Location**: `logs/agent.log`
- **Format**: `timestamp - logger - level - message`
- **Level**: Configurable via `LOG_LEVEL` env var

### Debug Mode

```bash
DEBUG=true streamlit run src/app.py
```

Shows additional console output and raw state inspection.

## 🚨 Error Handling

### Common Issues

1. **"Cannot find Google API key"**
   - Set `GOOGLE_API_KEY` in `.env`

2. **"Graph stuck at approval gate"**
   - Ensure `approval_granted` is set before resuming

3. **"Socket hang up / Connection refused"**
   - Check if Streamlit port 8501 is available
   - Kill any existing processes: `lsof -ti :8501 | xargs kill -9`

4. **"No module named 'src'"**
   - Add `src` to Python path or run from project root

## 🧬 Extending the Agent

### Add New Node

```python
# src/agent/nodes.py
def my_new_node(state: PortfolioState) -> PortfolioState:
    """Custom node logic"""
    # Modify state
    return state

# src/agent/graph.py - add to workflow:
workflow.add_node("my_node", my_new_node)
```

### Add New Tool

```python
# src/tools/my_tool.py
class MyTool:
    def do_something(self):
        pass

# Use in nodes:
from src.tools.my_tool import MyTool
tool = MyTool()
```

### Add New Visualization

```python
# src/ui/portfolio_viz.py
def render_custom_chart():
    """Custom visualization"""
    fig = px.scatter(...)
    st.plotly_chart(fig)
```

## 📚 Key Dependencies

| Package | Purpose |
|---------|---------|
| `langgraph` | Agent orchestration |
| `langchain` | LLM frameworks |
| `google-generativeai` | Gemini API |
| `streamlit` | Web UI |
| `pandas` | Data manipulation |
| `plotly` | Interactive charts |
| `pydantic` | Config validation |
| `langsmith` | Observability |

## 🔐 Security Considerations

1. **Never commit `.env` file** - Add to `.gitignore`
2. **API keys in env vars** - Not in code
3. **Input validation** - Stock symbols must be alphanumeric
4. **Trade limits** - Max 1000 shares per trade (configurable)
5. **Session isolation** - Per-user checkpoints prevent cross-contamination
6. **Approval audit** - All trades logged with timestamp

## 📝 API Reference

### Key Functions

#### Agent Graph

```python
from src.agent.graph import get_graph, initialize_state, invoke_agent

# Get compiled graph
graph = get_graph()

# Initialize state
state = initialize_state(thread_id="user-123")

# Invoke
result = invoke_agent(state, thread_id="user-123")
```

#### Tools

```python
from src.tools.stock_simulator import get_simulator
from src.tools.currency_converter import get_converter

simulator = get_simulator()
prices = simulator.get_batch_prices(["AAPL", "GOOGL"])

converter = get_converter()
eur_value = converter.convert(1000, "USD", "EUR")
```

#### Session

```python
from src.utils.session import init_session_state, get_thread_config

init_session_state()
config = get_thread_config()
```

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Add tests in `tests/`
3. Run: `pytest tests/ -v`
4. Submit pull request

## 📄 License

MIT License - See LICENSE file

## 🙋 Support

- **Issues**: GitHub Issues
- **Docs**: See [stock_trading_agent_lld_v1.md](stock_trading_agent_lld_v1.md)
- **Questions**: Create Discussion

---

**Built with ❤️ using LangGraph, Google Gemini & Streamlit**

**v0.1.0** | Last Updated: April 2026
