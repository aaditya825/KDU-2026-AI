"""
app/controllers/processing_controller.py
─────────────────────────────────────────
Orchestrates the Phase-2 processing flow for a single file:

    lookup → route → extract → post-process → persist → return result

All dependencies are built from settings defaults and can be overridden via
constructor arguments (useful for testing).
"""

from __future__ import annotations

from app.config.settings import settings
from app.models.domain import FileMetadata, FileStatus, ProcessingResult
from app.pipelines.content_router import ContentRouter
from app.repositories.file_repository import FileRepository
from app.repositories.processing_repository import ProcessingRepository
from app.services.post_processor import PostProcessor
from app.utils.logging_utils import get_logger
from app.utils.timing import Timer

log = get_logger(__name__)


def _build_llm():
    from app.adapters.llm_adapter import build_llm_adapter
    return build_llm_adapter(
        provider=settings.default_llm_provider,
        model=settings.default_llm_model,
        api_keys={
            "gemini": settings.gemini_api_key,
            "openai": settings.openai_api_key,
        },
    )


class ProcessingController:
    """Entry point for CLI and (later) Streamlit process flows."""

    def __init__(
        self,
        file_repo: FileRepository | None = None,
        proc_repo: ProcessingRepository | None = None,
        router: ContentRouter | None = None,
        post_processor: PostProcessor | None = None,
    ) -> None:
        self._file_repo = file_repo or FileRepository()
        self._proc_repo = proc_repo or ProcessingRepository()
        self._router = router or ContentRouter()
        self._post_processor = post_processor or PostProcessor(llm=_build_llm())

    def process_file(self, file_id: str) -> ProcessingResult:
        """
        Run the full extraction + post-processing pipeline for *file_id*.

        Returns
        -------
        ProcessingResult
            Populated result with cleaned text, summary, key points, and tags.

        Raises
        ------
        ValueError
            If *file_id* does not exist in the database.
        RuntimeError
            If extraction produces empty text (hard failure).
        """
        meta: FileMetadata | None = self._file_repo.get(file_id)
        if meta is None:
            raise ValueError(f"File '{file_id}' not found. Run 'ingest' first.")

        log.info("Processing started", extra={"file_id": file_id, "file_type": meta.file_type.value})
        self._file_repo.update_status(file_id, FileStatus.PROCESSING)
        extraction = None

        try:
            with Timer("processing.total") as t:
                pipeline = self._router.get_pipeline(meta)
                extraction = pipeline.process(meta.stored_path)

                if not extraction.raw_text.strip():
                    self._file_repo.update_status(file_id, FileStatus.FAILED)
                    raise RuntimeError(
                        f"Extraction produced no text for file '{file_id}'. "
                        f"Warnings: {extraction.warnings}"
                    )

                result = self._post_processor.process(file_id, extraction)

            self._proc_repo.save_processing_result(result)
            self._file_repo.update_status(file_id, FileStatus.COMPLETED)

        except Exception as exc:
            self._proc_repo.save_processing_result(
                ProcessingResult(
                    file_id=file_id,
                    extraction=extraction,
                    error_message=str(exc),
                )
            )
            self._file_repo.update_status(file_id, FileStatus.FAILED)
            raise

        log.info(
            "Processing complete",
            extra={"file_id": file_id, "latency_ms": t.elapsed_ms},
        )
        return result
