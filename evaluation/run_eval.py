"""Run a lightweight local evaluation over the trading agent graph."""
from pathlib import Path
from pprint import pprint
import sys

from langchain_core.messages import HumanMessage

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from evaluation.datasets import EVALUATION_CASES
from evaluation.metrics import compute_summary, evaluate_case
from src.trading_agent.orchestration.graph import initialize_state, invoke_agent


def run_local_evaluation() -> dict:
    """Execute all predefined evaluation cases."""
    case_results: list[dict] = []

    for case in EVALUATION_CASES:
        thread_id = f"eval-{case['name']}"
        state = initialize_state(thread_id, seed_portfolio=case.get("seed_portfolio", {}))
        state["messages"] = [HumanMessage(content=case["message"])]
        state["currency"] = case.get("initial_currency", "USD")

        result = invoke_agent(state, thread_id)
        checks = evaluate_case(result, case["expected"])
        case_results.append(
            {
                "name": case["name"],
                "checks": checks,
                "passed": all(checks.values()),
                "result": {
                    "current_step": result.get("current_step"),
                    "requires_approval": result.get("requires_approval"),
                    "pending_trade": result.get("pending_trade"),
                    "total_value": result.get("total_value"),
                    "currency": result.get("currency"),
                },
            }
        )

    return {
        "cases": case_results,
        "summary": compute_summary(case_results),
    }


if __name__ == "__main__":
    pprint(run_local_evaluation())
