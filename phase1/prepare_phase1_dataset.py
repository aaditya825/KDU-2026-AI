"""Generate and validate the Phase 1 JSONL dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

OUTPUT_PATH = Path("data/company_syntax_train.jsonl")

SYSTEM_PROMPT = (
    "You are the company syntax normalizer. Return strict JSON only using the "
    "approved schema keys. Do not add markdown, prose, or comments."
)

LLAMA3_BEGIN_OF_TEXT = "<|begin_of_text|>"
LLAMA3_START_HEADER = "<|start_header_id|>"
LLAMA3_END_HEADER = "<|end_header_id|>"
LLAMA3_END_OF_TURN = "<|eot_id|>"

REQUEST_TYPES: list[dict[str, str]] = [
    {"code": "HDO", "expansion": "handover", "request_type": "operations_handover"},
    {"code": "INC", "expansion": "incident", "request_type": "service_incident"},
    {"code": "RCA", "expansion": "root_cause_analysis", "request_type": "post_incident_review"},
    {"code": "CAPA", "expansion": "corrective_action_preventive_action", "request_type": "corrective_action_plan"},
    {"code": "CRQ", "expansion": "change_request", "request_type": "planned_change"},
    {"code": "CAB", "expansion": "change_advisory_board_review", "request_type": "change_review"},
    {"code": "IAM", "expansion": "identity_and_access_management", "request_type": "access_request"},
    {"code": "UAT", "expansion": "user_acceptance_testing", "request_type": "release_validation"},
    {"code": "DR", "expansion": "disaster_recovery", "request_type": "recovery_readiness"},
    {"code": "KBA", "expansion": "knowledge_base_article", "request_type": "knowledge_publish"},
]

DEPARTMENTS: list[dict[str, str]] = [
    {"code": "OPS", "name": "Operations"},
    {"code": "NET", "name": "Network Engineering"},
    {"code": "SEC", "name": "Security Operations"},
    {"code": "FIN", "name": "Finance Systems"},
    {"code": "HR", "name": "Human Resources Systems"},
]

PRIORITY_POOL: list[str] = ["P1", "P2", "P3", "P2", "P1"]

PROMPT_TEMPLATES: list[str] = [
    "Convert this {priority} {code} request for team {dept} into the company JSON schema.",
    "Normalize acronym {code} for department {dept} with {priority} priority and return strict JSON only.",
    "Format the internal {dept} {code} workflow as the approved response object. Severity is {priority}.",
    "Translate company shorthand {code} for team {dept}. Use the standard schema and mark priority as {priority}.",
    "Create the final machine-readable company record for {dept} / {code} / {priority}. Return JSON only.",
]


def render_llama3_text(messages: list[dict[str, str]]) -> str:
    """Render chat messages in Llama 3 format."""
    parts = [LLAMA3_BEGIN_OF_TEXT]
    for message in messages:
        parts.append(
            f"{LLAMA3_START_HEADER}{message['role']}{LLAMA3_END_HEADER}\n\n"
            f"{message['content']}{LLAMA3_END_OF_TURN}"
        )
    return "".join(parts)


def build_examples() -> list[dict[str, Any]]:
    """Build the 50 dataset examples."""
    examples: list[dict[str, Any]] = []

    for example_index, (request, department) in enumerate(
        (req, dept) for req in REQUEST_TYPES for dept in DEPARTMENTS
    ):
        request_index = example_index // len(DEPARTMENTS)
        dept_index = example_index % len(DEPARTMENTS)
        priority = PRIORITY_POOL[(request_index + dept_index) % len(PRIORITY_POOL)]
        prompt_template = PROMPT_TEMPLATES[example_index % len(PROMPT_TEMPLATES)]

        assistant_payload: dict[str, str] = {
            "request_code": request["code"],
            "request_expansion": request["expansion"],
            "request_type": request["request_type"],
            "department": department["code"],
            "department_name": department["name"],
            "priority": priority,
        }

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": prompt_template.format(
                    priority=priority,
                    code=request["code"],
                    dept=department["code"],
                ),
            },
            {
                "role": "assistant",
                "content": json.dumps(assistant_payload, separators=(",", ":")),
            },
        ]

        examples.append(
            {
                "messages": messages,
                "text": render_llama3_text(messages),
            }
        )

    return examples


def validate_examples(examples: list[dict[str, Any]]) -> None:
    """Validate row count, role order, JSON, and turn markers."""
    expected_count = 50
    expected_roles = ["system", "user", "assistant"]
    expected_eot_count = 3  # one per turn

    if len(examples) != expected_count:
        raise ValueError(f"Expected {expected_count} examples, found {len(examples)}")

    for i, example in enumerate(examples, start=1):
        messages = example["messages"]
        roles = [message["role"] for message in messages]
        if roles != expected_roles:
            raise ValueError(f"Example {i}: invalid role order {roles!r}")

        assistant_content = messages[-1]["content"]
        try:
            json.loads(assistant_content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Example {i}: assistant content is not valid JSON - {exc}") from exc

        text = example["text"]
        if not text.startswith(LLAMA3_BEGIN_OF_TEXT):
            raise ValueError(f"Example {i}: text does not start with {LLAMA3_BEGIN_OF_TEXT!r}")

        eot_count = text.count(LLAMA3_END_OF_TURN)
        if eot_count != expected_eot_count:
            raise ValueError(
                f"Example {i}: found {eot_count} {LLAMA3_END_OF_TURN!r} tokens, "
                f"expected {expected_eot_count}"
            )

        if not text.endswith(LLAMA3_END_OF_TURN):
            raise ValueError(f"Example {i}: text must end with {LLAMA3_END_OF_TURN!r}")


def write_jsonl(path: Path, examples: list[dict[str, Any]]) -> None:
    """Write the dataset to JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for example in examples:
            handle.write(json.dumps(example, ensure_ascii=True))
            handle.write("\n")


def maybe_preview_with_datasets(path: Path) -> None:
    """Optionally preview the file with Hugging Face datasets."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets package not installed; skipping Hugging Face preview.")
        return

    dataset = load_dataset("json", data_files=str(path), split="train")
    print(f"Hugging Face datasets preview - rows loaded: {len(dataset)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and validate the Phase 1 dataset.")
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help=f"Output JSONL path. Default: {OUTPUT_PATH}",
    )
    parser.add_argument(
        "--preview-hf",
        action="store_true",
        help="Preview the file with Hugging Face datasets after writing.",
    )
    args = parser.parse_args()

    examples = build_examples()
    validate_examples(examples)
    write_jsonl(args.output, examples)

    print(f"Wrote {len(examples)} examples to {args.output}")
    print(f"Sample assistant output: {examples[0]['messages'][-1]['content']}")

    if args.preview_hf:
        maybe_preview_with_datasets(args.output)


if __name__ == "__main__":
    main()
