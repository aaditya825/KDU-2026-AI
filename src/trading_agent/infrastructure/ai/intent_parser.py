"""Intent parser implementations."""
import json
import re

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config.settings import settings
from src.trading_agent.domain import IntentDecision, IntentParser, PortfolioState
from src.utils.logger import logger


class GeminiIntentParser(IntentParser):
    """LLM intent parser with deterministic fallback rules."""

    _EXCLUDED_SYMBOL_TOKENS = {"BUY", "SELL", "SHOW", "VALUE", "IN", "USD", "INR", "EUR"}
    _DEFAULT_MODEL = "gemini-1.5-pro"

    def parse(self, user_message: str, state: PortfolioState) -> IntentDecision:
        """Parse user message into an intent decision."""
        decision = self._try_llm_parse(user_message, state)
        if decision is not None:
            return decision
        return self._fallback_parse(user_message)

    def _try_llm_parse(self, user_message: str, state: PortfolioState) -> IntentDecision | None:
        """Use Gemini when credentials are available."""
        if not settings.google_api_key:
            return None

        prompt = f"""
Analyze this user request: "{user_message}"

Current portfolio: {state.get('holdings', {})}
Current currency: {state.get('currency', 'USD')}

Determine the action needed. Choose ONE:
- "calculate_portfolio": User wants to know portfolio value
- "buy_stock": User wants to buy stocks (extract symbol, quantity)
- "sell_stock": User wants to sell stocks (extract symbol, quantity)
- "change_currency": User wants different currency display (extract target like USD, INR, EUR)
- "view_holdings": User wants to see current positions
- "help": User needs assistance

For trades, extract symbol (uppercase) and quantity (number).

Respond ONLY with valid JSON, no extra text:
{{"action": "...", "params": {{...}}}}
"""
        try:
            llm = ChatGoogleGenerativeAI(
                model=self._DEFAULT_MODEL,
                google_api_key=settings.google_api_key,
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            intent_text = response.content.strip()
            json_match = re.search(r"\{.*\}", intent_text, re.DOTALL)
            parsed = json.loads(json_match.group() if json_match else intent_text)
            return IntentDecision(
                action=parsed.get("action", "help"),
                params=parsed.get("params", {}),
            )
        except Exception as exc:
            logger.warning(f"LLM intent parsing failed, using fallback parser: {exc}")
            return None

    def _fallback_parse(self, user_message: str) -> IntentDecision:
        """Rule-based parser for local/dev mode."""
        text = user_message.strip()
        lower = text.lower()

        def extract_symbol() -> str:
            candidates = re.findall(r"\b([A-Z]{1,5})\b", text.upper())
            for candidate in candidates:
                if candidate not in self._EXCLUDED_SYMBOL_TOKENS:
                    return candidate
            return ""

        currency_match = re.search(r"\b(usd|inr|eur)\b", lower)
        if any(keyword in lower for keyword in ["currency", "convert", "show value in", "display in"]) and currency_match:
            return IntentDecision(
                action="change_currency",
                params={"currency": currency_match.group(1).upper()},
            )

        if any(keyword in lower for keyword in ["buy", "purchase"]):
            quantity_match = re.search(r"\b(\d+)\b", text)
            return IntentDecision(
                action="buy_stock",
                params={
                    "symbol": extract_symbol(),
                    "quantity": int(quantity_match.group(1)) if quantity_match else 1,
                },
            )

        if any(keyword in lower for keyword in ["sell", "offload"]):
            quantity_match = re.search(r"\b(\d+)\b", text)
            return IntentDecision(
                action="sell_stock",
                params={
                    "symbol": extract_symbol(),
                    "quantity": int(quantity_match.group(1)) if quantity_match else 1,
                },
            )

        if any(keyword in lower for keyword in ["approve", "approved", "yes", "confirm"]):
            return IntentDecision(action="approval_response", params={"approved": True})

        if any(keyword in lower for keyword in ["reject", "rejected", "no", "cancel"]):
            return IntentDecision(action="approval_response", params={"approved": False})

        if any(keyword in lower for keyword in ["worth", "value", "total", "portfolio value"]):
            return IntentDecision(action="calculate_portfolio")

        if any(keyword in lower for keyword in ["holdings", "positions", "show portfolio", "my portfolio"]):
            return IntentDecision(action="view_holdings")

        if any(keyword in lower for keyword in ["hi", "hello", "hey"]):
            return IntentDecision(action="view_holdings")

        return IntentDecision(action="help")
