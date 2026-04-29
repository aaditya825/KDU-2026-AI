"""Report/export helpers with explicit filesystem error handling."""

from __future__ import annotations

import re
from pathlib import Path

from app.config.settings import settings
from app.utils.exceptions import ReportExportError, classify_os_error, ensure_path_within


def _safe_report_name(name: str) -> str:
    safe = re.sub(r"[^\w.\-]", "_", Path(name).name).strip("_.")
    return safe[:180] or "report.txt"


class ReportService:
    """Writes generated reports under the controlled reports directory."""

    def __init__(self, reports_dir: str | Path = "reports") -> None:
        self._reports_dir = Path(reports_dir)

    def write_text_report(self, filename: str, content: str) -> Path:
        if not content.strip():
            raise ReportExportError("Cannot export an empty report.")

        target = self._reports_dir / _safe_report_name(filename)
        ensure_path_within(self._reports_dir, target)
        if len(str(target.resolve())) > settings.max_path_chars:
            raise ReportExportError(
                f"Report path is too long ({len(str(target.resolve()))} characters).",
                remediation="Use a shorter report filename or move the project to a shorter path.",
            )

        try:
            self._reports_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise classify_os_error(exc, action="write the report export") from exc

        return target
