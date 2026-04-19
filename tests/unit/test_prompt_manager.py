import json
import shutil
from pathlib import Path
from uuid import uuid4

from src.prompt_manager.metadata_tracker import PromptMetadataTracker
from src.prompt_manager.prompt_manager import PromptManager


def test_prompt_manager_loads_prompt_version() -> None:
    prompt = PromptManager(Path("prompts")).load("faq", 1)

    assert prompt.key == "faq"
    assert prompt.version == 1
    assert "home services marketplace" in prompt.template


def test_prompt_manager_renders_query_variable() -> None:
    manager = PromptManager(Path("prompts"))
    prompt = manager.load("booking", 1)

    rendered = manager.render(prompt, {"query": "Can I reschedule my appointment?"})

    assert "{{ query }}" not in rendered
    assert "Can I reschedule my appointment?" in rendered


def test_prompt_manager_merges_runtime_metadata() -> None:
    sandbox_dir = Path.cwd() / f"prompt-manager-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        metrics_path = sandbox_dir / "prompt_metrics.json"
        metrics_path.write_text(
            json.dumps(
                {
                    "faq:1": {
                        "usage_count": 3,
                        "success_count": 2,
                        "failure_count": 1,
                        "last_used_at": "2026-04-19T12:00:00+00:00",
                    }
                }
            ),
            encoding="utf-8",
        )
        manager = PromptManager(
            Path("prompts"),
            metadata_tracker=PromptMetadataTracker(metrics_path),
        )

        prompt = manager.load("faq", 1)

        assert prompt.runtime_metadata.usage_count == 3
        assert prompt.runtime_metadata.success_count == 2
        assert prompt.runtime_metadata.failure_count == 1
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


def test_prompt_manager_falls_back_to_base_prompt_when_selected_missing() -> None:
    manager = PromptManager(Path("prompts"))

    prompt, reason = manager.load_with_fallback(
        "missing-prompt",
        1,
        fallback_key="base",
        fallback_version=1,
    )

    assert prompt.key == "base"
    assert prompt.version == 1
    assert reason is not None
