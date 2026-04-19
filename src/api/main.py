"""Local application entry point."""

from __future__ import annotations

from src.api.service import build_local_application


def main() -> None:
    """Run a sample local query through the application pipeline."""
    app = build_local_application()
    result = app.handle_query("What are your hours?")
    print(
        f"Processed query {result.query_id} "
        f"with tier={result.model_tier}, model={result.model_id}, mode={result.mode}"
    )
    print(result.response_text)


if __name__ == "__main__":
    main()
