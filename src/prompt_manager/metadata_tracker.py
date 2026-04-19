"""Runtime prompt metadata tracking with local JSON persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.core.models import PromptRuntimeMetadata


class PromptMetadataTracker:
    """Tracks runtime prompt usage separately from static prompt files."""

    def __init__(self, metrics_path: Path) -> None:
        self.metrics_path = metrics_path
        self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.metrics_path.exists():
            self.metrics_path.write_text("{}", encoding="utf-8")

    def get_runtime_metadata(self, prompt_key: str, prompt_version: int) -> PromptRuntimeMetadata:
        store = self._load_store()
        record = store.get(self._record_key(prompt_key, prompt_version), {})
        return PromptRuntimeMetadata.model_validate(record)

    def record_usage(self, prompt_key: str, prompt_version: int) -> PromptRuntimeMetadata:
        store = self._load_store()
        record_key = self._record_key(prompt_key, prompt_version)
        metadata = PromptRuntimeMetadata.model_validate(store.get(record_key, {}))
        metadata.usage_count += 1
        metadata.last_used_at = datetime.now(UTC).isoformat()
        store[record_key] = metadata.model_dump()
        self._save_store(store)
        return metadata

    def record_outcome(
        self,
        prompt_key: str,
        prompt_version: int,
        *,
        success: bool,
        actual_cost: float | None = None,
        latency_ms: float | None = None,
        evaluation_score: float | None = None,
    ) -> PromptRuntimeMetadata:
        store = self._load_store()
        record_key = self._record_key(prompt_key, prompt_version)
        metadata = PromptRuntimeMetadata.model_validate(store.get(record_key, {}))

        if success:
            metadata.success_count += 1
        else:
            metadata.failure_count += 1

        if actual_cost is not None:
            completed_runs = metadata.success_count + metadata.failure_count
            if metadata.average_cost_usd is None or completed_runs <= 1:
                metadata.average_cost_usd = round(actual_cost, 6)
            else:
                previous_total = metadata.average_cost_usd * (completed_runs - 1)
                metadata.average_cost_usd = round(
                    (previous_total + actual_cost) / completed_runs,
                    6,
                )

        if latency_ms is not None:
            completed_runs = metadata.success_count + metadata.failure_count
            if metadata.average_latency_ms is None or completed_runs <= 1:
                metadata.average_latency_ms = round(latency_ms, 3)
            else:
                previous_total = metadata.average_latency_ms * (completed_runs - 1)
                metadata.average_latency_ms = round(
                    (previous_total + latency_ms) / completed_runs,
                    3,
                )

        if evaluation_score is not None:
            metadata.evaluation_score = evaluation_score

        store[record_key] = metadata.model_dump()
        self._save_store(store)
        return metadata

    @staticmethod
    def _record_key(prompt_key: str, prompt_version: int) -> str:
        return f"{prompt_key}:{prompt_version}"

    def _load_store(self) -> dict[str, dict]:
        with self.metrics_path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError(f"Prompt metadata store must contain an object: {self.metrics_path}")
        return loaded

    def _save_store(self, store: dict[str, dict]) -> None:
        with self.metrics_path.open("w", encoding="utf-8") as handle:
            json.dump(store, handle, indent=2, sort_keys=True)
