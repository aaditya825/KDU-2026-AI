"""
app/controllers/comparison_controller.py
─────────────────────────────────────────
Orchestrates Phase-3 model comparison for a single file.

Looks up the processed output, builds comparison configs from settings, and
delegates to ComparisonService.
"""

from __future__ import annotations

from app.config.settings import settings
from app.models.domain import ComparisonReport
from app.repositories.file_repository import FileRepository
from app.repositories.processing_repository import ProcessingRepository
from app.services.comparison_service import ComparisonService, build_comparison_configs
from app.utils.logging_utils import get_logger

log = get_logger(__name__)


class ComparisonController:
    """Entry point for the CLI 'compare' command and Phase-4 UI."""

    def __init__(
        self,
        file_repo: FileRepository | None = None,
        proc_repo: ProcessingRepository | None = None,
    ) -> None:
        self._file_repo = file_repo or FileRepository()
        self._proc_repo = proc_repo or ProcessingRepository()

    def compare(self, file_id: str) -> ComparisonReport:
        """
        Run model comparison for *file_id*.

        Returns
        -------
        ComparisonReport
            Per-model metrics and observations.

        Raises
        ------
        ValueError
            If the file does not exist or has not been processed.
        """
        if not self._file_repo.get(file_id):
            raise ValueError(f"File '{file_id}' not found. Run 'ingest' first.")

        output = self._proc_repo.get_processing_result(file_id)
        if output is None:
            raise ValueError(
                f"File '{file_id}' has not been processed yet. "
                "Run 'python -m app.cli process <file_id>' first."
            )

        cleaned_text = output.get("cleaned_text", "")
        if not cleaned_text:
            raise ValueError(f"No cleaned text available for file '{file_id}'.")

        configs = build_comparison_configs(
            gemini_key=settings.gemini_api_key,
            openai_key=settings.openai_api_key,
        )

        service = ComparisonService(configs=configs)
        report = service.compare(file_id=file_id, cleaned_text=cleaned_text)

        # Persist metrics
        for result in report.model_results:
            from app.models.domain import ModelMetric
            import uuid
            self._proc_repo.save_metric(
                ModelMetric(
                    metric_id=str(uuid.uuid4()),
                    file_id=file_id,
                    stage=result.get("stage", "comparison"),
                    model_name=result.get("model_name", ""),
                    provider=result.get("provider", ""),
                    latency_ms=result.get("latency_ms", 0),
                    estimated_cost=result.get("estimated_cost", 0.0),
                    status=result.get("status", "unknown"),
                    error_message=result.get("error_message", ""),
                )
            )

        log.info(
            "Comparison complete",
            extra={"file_id": file_id, "configs_run": len(configs)},
        )
        return report
