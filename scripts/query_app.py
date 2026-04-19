"""Interactive CLI for manually querying the FixIt app in the terminal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.service import build_local_application


def _format_result(result) -> str:
    lines = [
        f"Query ID: {result.query_id}",
        f"Category: {result.category}",
        f"Complexity: {result.complexity}",
        f"Model Tier: {result.model_tier}",
        f"Model ID: {result.model_id}",
        f"Prompt: {result.prompt_key}:v{result.prompt_version}",
        f"Mode: {result.mode}",
        f"Estimated Cost (USD): {result.estimated_cost}",
        f"Actual Cost (USD): {result.actual_cost}",
        "Response:",
        result.response_text,
    ]

    optional_metadata = {
        "Route Adjustment Reason": result.metadata.get("route_adjustment_reason"),
        "Prompt Fallback Reason": result.metadata.get("prompt_fallback_reason"),
        "Generation Fallback Reason": result.metadata.get("generation_fallback_reason"),
        "Budget Reason": result.metadata.get("budget_reason"),
    }
    for label, value in optional_metadata.items():
        if value:
            lines.append(f"{label}: {value}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the local FixIt app from the terminal.")
    parser.add_argument("query", nargs="?", help="Query to send to the local application.")
    args = parser.parse_args()

    app = build_local_application(PROJECT_ROOT)
    query = args.query
    if query:
        result = app.handle_query(query)
        print(_format_result(result))
        return

    print("Interactive FixIt CLI started. Type 'exit' or 'quit' to stop.")
    while True:
        try:
            query = input("Enter your FixIt query: ").strip()
        except EOFError:
            print("\nExiting interactive FixIt CLI.")
            break

        if not query:
            print("Query cannot be empty.")
            continue

        if query.lower() in {"exit", "quit"}:
            print("Exiting interactive FixIt CLI.")
            break

        result = app.handle_query(query)
        print(_format_result(result))
        print()


if __name__ == "__main__":
    main()
