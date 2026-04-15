"""Initialize local storage directories for the scaffold."""

from __future__ import annotations

from src.core.config import load_settings
from src.utils.helpers import ensure_directory


def main() -> None:
    settings = load_settings()
    ensure_directory(settings.storage.vector_store_path)
    ensure_directory(settings.storage.keyword_store_path)
    ensure_directory("data/raw")
    ensure_directory("data/processed")
    print("Initialized local data directories.")


if __name__ == "__main__":
    main()
