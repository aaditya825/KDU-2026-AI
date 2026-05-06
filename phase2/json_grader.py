"""Binary JSON validity grader for RFT."""

from __future__ import annotations

import argparse
import json
from typing import Iterable


def grade_json_output(model_output: str) -> float:
    """Return 1.0 for valid JSON and -1.0 for invalid JSON."""
    try:
        json.loads(model_output)
    except json.JSONDecodeError:
        return -1.0
    return 1.0


def explain_reward_usage() -> str:
    """Summarize how the reward is used in PPO and DPO."""
    return (
        "PPO uses this score directly during training: valid JSON gets a "
        "positive reward and invalid JSON gets a negative reward, so the "
        "policy is updated toward outputs that parse correctly.\n"
        "DPO uses the same rule to define preference pairs: valid JSON is the "
        "chosen response and invalid JSON is the rejected response."
    )


def run_examples(examples: Iterable[str]) -> None:
    """Print the score for each example string."""
    for example in examples:
        score = grade_json_output(example)
        label = "PASS" if score == 1.0 else "FAIL"
        print(f"[{label}]  score={score:+.1f}  input={example!r}")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="json_grader.py",
        description="Score model outputs as valid (1.0) or invalid (-1.0) JSON.",
    )
    parser.add_argument(
        "--text",
        metavar="STRING",
        help="A single model output string to grade.",
    )
    parser.add_argument(
        "--show-examples",
        action="store_true",
        help="Run built-in grading examples.",
    )
    parser.add_argument(
        "--show-rft-notes",
        action="store_true",
        help="Print PPO and DPO reward usage notes.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.text is None and not args.show_examples and not args.show_rft_notes:
        parser.print_help()
        return

    if args.text is not None:
        score = grade_json_output(args.text)
        label = "PASS" if score == 1.0 else "FAIL"
        print(f"[{label}]  score={score:+.1f}")

    if args.show_examples:
        run_examples(
            [
                '{"request_type":"handover","code":"HDO"}',
                '{"request_type":"handover","code":HDO}',
                '{"priority":"P1","department":"NET"}',
                "not json at all",
                "",
                "null",
                '{"broken": }',
            ]
        )

    if args.show_rft_notes:
        print(explain_reward_usage())


if __name__ == "__main__":
    main()
