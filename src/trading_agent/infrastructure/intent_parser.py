"""Intent parser implementations."""
import json
import re

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config.settings import settings
from src.trading_agent.domain import IntentDecision, IntentParser, PortfolioState
from src.utils.logger import logger


class GeminiIntentParser(IntentParser):
    """LLM parser with deterministic fallback rules."""

    _EXCLUDED_SYMBOL_TOKENS = {"BUY", "SELL", "SHOW", "VALUE", "IN", "USD", "INR", "EUR"}
    _DEFAULT_MODEL = "gemini-1.5-pro"

    def parse(self, user_message: str, state: PortfolioState) -> IntentDecision:
        """Parse a user message into a supported action."""
        decision = self._try_llm_parse(user_message, state)
        if decision is not None:
            return decision
        return self._fallback_parse(user_message)

    def _try_llm_parse(self, user_message: str, state: PortfolioState) -> IntentDecision | None:
        """Use Gemini parsing when API credentials are configured."""
        if not settings.google_api_key:
            return None

        prompt = f"""
Analyze this user request: "{user_message}"

Current portfolio: {state.get('holdings', {})}
Current currency: {state.get('currency', 'USD')}

Choose exactly one action:
- calculate_portfolio
- buy_stock
- sell_stock
- change_currency
- view_holdings
- help

For trades, extract symbol and quantity.
For currency changes, extract USD, INR, or EUR.

Respond with JSON only:
{{"action": "...", "params": {{...}}}}
"""
        try:
            llm = ChatGoogleGenerativeAI(
                model=self._DEFAULT_MODEL,
                google_api_key=settings.google_api_key,
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            content = str(response.content).strip()
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            parsed = json.loads(json_match.group() if json_match else content)
            return IntentDecision(
                action=parsed.get("action", "help"),
                params=parsed.get("params", {}),
            )
        except Exception as exc:
            logger.warning("LLM intent parsing failed. Falling back to rules. Error: %s", exc)
            return None

    def _fallback_parse(self, user_message: str) -> IntentDecision:
        """Deterministic fallback parser for local runs and tests."""
        text = user_message.strip()
        lower = text.lower()

        def extract_symbol() -> str:
            candidates = re.findall(r"\b([A-Z]{1,5})\b", text.upper())
            for candidate in candidates:
                if candidate not in self._EXCLUDED_SYMBOL_TOKENS:
                    return candidate
            return ""

        quantity_match = re.search(r"\b(\d+)\b", text)
        currency_match = re.search(r"\b(usd|inr|eur)\b", lower)

        if any(keyword in lower for keyword in {"currency", "convert", "display in", "show value in"}) and currency_match:
            return IntentDecision(
                action="change_currency",
                params={"currency": currency_match.group(1).upper()},
            )

        if any(keyword in lower for keyword in {"buy", "purchase"}):
            return IntentDecision(
                action="buy_stock",
                params={"symbol": extract_symbol(), "quantity": int(quantity_match.group(1)) if quantity_match else 1},
            )

        if any(keyword in lower for keyword in {"sell", "offload"}):
            return IntentDecision(
                action="sell_stock",
                params={"symbol": extract_symbol(), "quantity": int(quantity_match.group(1)) if quantity_match else 1},
            )

        if any(keyword in lower for keyword in {"approve", "approved", "yes", "confirm"}):
            return IntentDecision(action="approval_response", params={"approved": True})

        if any(keyword in lower for keyword in {"reject", "rejected", "no", "cancel"}):
            return IntentDecision(action="approval_response", params={"approved": False})

        if any(keyword in lower for keyword in {"worth", "value", "total", "portfolio value"}):
            return IntentDecision(action="calculate_portfolio")

        if any(keyword in lower for keyword in {"holdings", "positions", "show portfolio", "my portfolio", "hello", "hi"}):
            return IntentDecision(action="view_holdings")

        return IntentDecision(action="help")
