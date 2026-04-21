from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
from textwrap import fill
from typing import Sequence

from tri_model_assistant.core.config import AppConfig
from tri_model_assistant.core.orchestrator import QueryRoutedAssistant
from tri_model_assistant.core.router import QueryRouter, Route
from tri_model_assistant.core.state import AssistantState
from tri_model_assistant.models.pipeline import TriModelModelGateway
from tri_model_assistant.models.qa import HuggingFaceQAClient

DIVIDER = "=" * 72
SUBDIVIDER = "-" * 72
LOGGER = logging.getLogger(__name__)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exercise 3 query-routed multi-model assistant."
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Path to a text file to load as the assistant's document context. If omitted, the program will prompt for pasted input.",
    )
    parser.add_argument(
        "--query",
        help="Run a single routed query and exit.",
    )
    parser.add_argument(
        "--show-route",
        action="store_true",
        help="Print the selected route and routing reason for each query.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.ERROR)
    try:
        parser = build_argument_parser()
        args = parser.parse_args(argv)

        config = AppConfig()
        source_text = _load_input_text(args.input_file)
        assistant = QueryRoutedAssistant(
            assistant_state=AssistantState(original_text=source_text),
            router=QueryRouter(),
            model_gateway=TriModelModelGateway(config),
            qa_client=HuggingFaceQAClient(config),
        )
    except (OSError, ValueError, RuntimeError) as exc:
        return _exit_with_error(str(exc))

    _print_banner()
    print(_format_text("Document stored and ready. Ask for a summary, request a shorter or longer version, or ask a grounded question about the document."))

    if args.query:
        try:
            outcome = assistant.handle_query(args.query)
        except RuntimeError as exc:
            LOGGER.exception("Single-query execution failed.")
            return _exit_with_error(f"Failed to process query: {exc}")
        _print_outcome(outcome, show_route=args.show_route)
        return 0

    return _run_query_loop(assistant=assistant, show_route=args.show_route)


def _load_input_text(input_file: Path | None) -> str:
    if input_file is not None:
        if not input_file.exists():
            raise ValueError(f"Input file does not exist: {input_file}")
        if not input_file.is_file():
            raise ValueError(f"Input path is not a file: {input_file}")

        source_text = input_file.read_text(encoding="utf-8")
        return _validate_source_text(source_text)

    print(DIVIDER)
    print("SOURCE DOCUMENT")
    print(SUBDIVIDER)
    print(_format_text("Paste the source text below. Finish with Ctrl+Z then Enter on Windows, or Ctrl+D on macOS/Linux."))
    return _validate_source_text(_read_multiline_stdin())


def _read_multiline_stdin() -> str:
    lines: list[str] = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    return "\n".join(lines).strip()


def _run_query_loop(assistant: QueryRoutedAssistant, show_route: bool) -> int:
    print(f"\n{DIVIDER}")
    print("QUERY LOOP")
    print(SUBDIVIDER)
    print("Type 'exit' or 'quit' to stop.")
    while True:
        query = input("\nassistant> ").strip()
        if not query:
            print("Enter a non-empty query or type 'exit'.")
            continue

        try:
            outcome = assistant.handle_query(query)
        except RuntimeError as exc:
            LOGGER.exception("Interactive query execution failed.")
            _print_runtime_error(f"Failed to process query: {exc}")
            continue
        _print_outcome(outcome, show_route=show_route)
        if outcome.route is Route.EXIT:
            return 0


def _validate_source_text(source_text: str) -> str:
    if not source_text.strip():
        raise ValueError("Input document is empty. Provide a non-empty text file or pasted document.")
    return source_text


def _print_outcome(outcome, show_route: bool) -> None:
    print(f"\n{DIVIDER}")
    print("ASSISTANT RESPONSE")
    print(SUBDIVIDER)

    if show_route:
        print(_format_labeled_line("Route", outcome.route.value))
        print(_format_labeled_line("Reason", outcome.route_reason))
        if outcome.model_used:
            print(_format_labeled_line("Model Used", outcome.model_used))
        if outcome.context_source:
            print(_format_labeled_line("Context Source", outcome.context_source))
        print(SUBDIVIDER)

    print("Response")
    print(SUBDIVIDER)
    print(outcome.response)


def _print_banner() -> None:
    print(DIVIDER)
    print("EXERCISE 3 QUERY-ROUTED MULTI-MODEL ASSISTANT")
    print(DIVIDER)


def _format_text(text: str, width: int = 72, subsequent_indent: str = "") -> str:
    return fill(text, width=width, subsequent_indent=subsequent_indent)


def _format_labeled_line(label: str, value: str) -> str:
    prefix = f"{label:<14} : "
    return fill(
        value,
        width=len(DIVIDER),
        initial_indent=prefix,
        subsequent_indent=" " * len(prefix),
    )


def _print_runtime_error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def _exit_with_error(message: str) -> int:
    _print_runtime_error(message)
    return 1
