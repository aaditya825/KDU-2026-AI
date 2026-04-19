import json
import shutil
from pathlib import Path
from uuid import uuid4

from src.prompt_manager.metadata_tracker import PromptMetadataTracker


def test_prompt_metadata_tracker_records_usage_and_outcome() -> None:
    sandbox_dir = Path.cwd() / f"prompt-metadata-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        metrics_path = sandbox_dir / "prompt_metrics.json"
        tracker = PromptMetadataTracker(metrics_path)

        usage_metadata = tracker.record_usage("faq", 1)
        outcome_metadata = tracker.record_outcome(
            "faq",
            1,
            success=True,
            actual_cost=0.015,
            latency_ms=42.5,
        )

        assert usage_metadata.usage_count == 1
        assert outcome_metadata.success_count == 1
        assert outcome_metadata.average_cost_usd == 0.015
        assert outcome_metadata.average_latency_ms == 42.5

        persisted = json.loads(metrics_path.read_text(encoding="utf-8"))
        assert persisted["faq:1"]["usage_count"] == 1
        assert persisted["faq:1"]["success_count"] == 1
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)

