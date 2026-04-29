"""Application exceptions and user-facing error formatting."""

from __future__ import annotations

import errno
import os
import sqlite3
from pathlib import Path


class AppError(Exception):
    """Base class for expected, user-actionable application failures."""

    code = "app_error"

    def __init__(self, message: str, *, remediation: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.remediation = remediation

    def __str__(self) -> str:
        if self.remediation:
            return f"{self.message} {self.remediation}"
        return self.message


class AppValidationError(AppError, ValueError):
    code = "validation_error"


class ProcessingError(AppError, RuntimeError):
    code = "processing_error"


class DependencyError(AppError, RuntimeError):
    code = "dependency_error"


class StorageError(AppError, OSError):
    code = "storage_error"


class DatabaseError(AppError, RuntimeError):
    code = "database_error"


class RetrievalError(AppError, RuntimeError):
    code = "retrieval_error"


class ModelProviderError(AppError, RuntimeError):
    code = "model_provider_error"


class AppTimeoutError(AppError, TimeoutError):
    code = "timeout_error"


class ReportExportError(AppError, OSError):
    code = "report_export_error"


def classify_sqlite_error(exc: sqlite3.Error) -> DatabaseError:
    """Return a stable, user-facing database error."""
    msg = str(exc)
    lowered = msg.lower()
    if "locked" in lowered or "busy" in lowered:
        return DatabaseError(
            "SQLite database is locked by another process.",
            remediation="Close other app/test sessions using the DB and retry.",
        )
    if "no such table" in lowered or "no such column" in lowered or "schema" in lowered:
        return DatabaseError(
            "SQLite schema is missing or incompatible.",
            remediation="Delete the local runtime DB under data/sqlite/ or run migrations before retrying.",
        )
    if "readonly" in lowered or "permission" in lowered:
        return DatabaseError(
            "SQLite database is not writable.",
            remediation="Check folder permissions for the configured SQLITE_DB_PATH.",
        )
    if "disk" in lowered and ("full" in lowered or "i/o" in lowered):
        return DatabaseError(
            "SQLite could not write because disk space or disk I/O failed.",
            remediation="Free disk space, check the DATA_DIR drive, and retry.",
        )
    return DatabaseError(f"SQLite operation failed: {msg}")


def classify_os_error(exc: OSError, *, action: str) -> StorageError:
    """Return a stable, user-facing filesystem/storage error."""
    path = getattr(exc, "filename", None)
    path_msg = f" Path: {path}" if path else ""
    if isinstance(exc, PermissionError) or exc.errno == errno.EACCES:
        return StorageError(
            f"Permission denied while trying to {action}.{path_msg}",
            remediation="Check file/folder permissions and close programs that may be locking the file.",
        )
    if exc.errno == errno.ENOSPC:
        return StorageError(
            f"Insufficient disk space while trying to {action}.{path_msg}",
            remediation="Free disk space or change DATA_DIR to a drive with enough space.",
        )
    if exc.errno in {errno.ENAMETOOLONG, getattr(errno, "E2BIG", 7)}:
        return StorageError(
            f"Path or filename is too long while trying to {action}.{path_msg}",
            remediation="Use a shorter filename or move the project to a shorter path.",
        )
    return StorageError(f"Filesystem error while trying to {action}: {exc}")


def classify_external_error(exc: Exception, *, provider: str) -> ModelProviderError:
    """Normalize model/cloud/dependency failures into a useful message."""
    msg = str(exc)
    lowered = msg.lower()
    if "api key" in lowered or "unauthorized" in lowered or "authentication" in lowered:
        return ModelProviderError(
            f"{provider} authentication failed.",
            remediation="Check the API key in .env or switch to local fallback.",
        )
    if "quota" in lowered or "insufficient_quota" in lowered:
        return ModelProviderError(
            f"{provider} quota is exhausted.",
            remediation="Check provider quota/billing or use another configured provider.",
        )
    if "rate" in lowered and "limit" in lowered:
        return ModelProviderError(
            f"{provider} rate limit was reached.",
            remediation="Retry later or reduce request frequency.",
        )
    if "timeout" in lowered or "timed out" in lowered:
        return ModelProviderError(
            f"{provider} request timed out.",
            remediation="Retry, reduce input size, or use a fallback provider.",
        )
    if any(term in lowered for term in ("connection", "network", "dns", "ssl", "resolve")):
        return ModelProviderError(
            f"{provider} request failed due to network connectivity.",
            remediation="Check internet access or use local fallback.",
        )
    if isinstance(exc, MemoryError) or "memory" in lowered or "out of memory" in lowered:
        return ModelProviderError(
            f"{provider} failed because the model/runtime ran out of memory.",
            remediation="Use a smaller model, reduce input size, or close other processes.",
        )
    return ModelProviderError(f"{provider} call failed: {msg}")


def ensure_path_within(base: Path, target: Path) -> None:
    """Guard report/export paths from escaping their intended directory."""
    base_resolved = base.resolve()
    target_resolved = target.resolve()
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise ReportExportError(
            f"Refusing to write outside the reports directory: {target}",
        ) from exc


def format_user_error(exc: Exception, *, prefix: str = "Operation failed") -> str:
    """Format exceptions for CLI/Streamlit without exposing noisy traces."""
    if isinstance(exc, AppError):
        return str(exc)
    if isinstance(exc, sqlite3.Error):
        return str(classify_sqlite_error(exc))
    if isinstance(exc, OSError):
        return str(classify_os_error(exc, action=prefix.lower()))
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, RuntimeError):
        return str(exc)
    if isinstance(exc, ImportError):
        return f"Missing dependency: {exc}"
    if isinstance(exc, MemoryError):
        return "Operation failed because the runtime ran out of memory. Reduce input size or close other processes."
    if os.environ.get("CAS_DEBUG_ERRORS", "").lower() in {"1", "true", "yes"}:
        return f"{prefix}: {exc!r}"
    return f"{prefix}: {exc}"
