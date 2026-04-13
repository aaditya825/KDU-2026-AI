"""Basic evaluation metrics for local runs."""
from typing import Any


def evaluate_case(result: dict[str, Any], expected: dict[str, Any]) -> dict[str, bool]:
    """Evaluate a single workflow result against a small expected contract."""
    checks = {
        "approval_match": result.get("requires_approval") == expected.get(
            "requires_approval", result.get("requires_approval")
        ),
    }

    if "pending_symbol" in expected:
        checks["pending_symbol_match"] = (
            result.get("pending_trade", {}) or {}
        ).get("symbol") == expected["pending_symbol"]

    if "min_total_value" in expected:
        checks["value_present"] = float(result.get("total_value", 0.0) or 0.0) >= expected["min_total_value"]

    return checks


def compute_summary(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a compact summary over all evaluated cases."""
    total_cases = len(case_results)
    passed_cases = sum(1 for case in case_results if case["passed"])
    total_checks = sum(len(case["checks"]) for case in case_results)
    passed_checks = sum(sum(1 for passed in case["checks"].values() if passed) for case in case_results)

    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "case_pass_rate": round((passed_cases / total_cases) * 100, 2) if total_cases else 0.0,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "check_pass_rate": round((passed_checks / total_checks) * 100, 2) if total_checks else 0.0,
    }
