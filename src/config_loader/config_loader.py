"""Config loader implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.core.models import ActiveConfig, PricingConfig


class ConfigLoader:
    """Loads and validates external configuration files."""

    def __init__(self, config_path: Path, pricing_path: Path | None = None) -> None:
        self.config_path = config_path
        self.pricing_path = pricing_path

    def load(self) -> ActiveConfig:
        """Load and validate active configuration."""
        raw_config = self._load_yaml(self.config_path)
        return ActiveConfig.model_validate(raw_config)

    def load_pricing(self) -> PricingConfig:
        """Load and validate pricing metadata."""
        if self.pricing_path is None:
            raise ValueError("A pricing file path was not provided.")

        raw_pricing = self._load_yaml(self.pricing_path)
        return PricingConfig.model_validate(raw_pricing)

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)

        if not isinstance(loaded, dict):
            raise ValueError(f"YAML root must be a mapping in file: {path}")

        return loaded


class ConfigManager:
    """Provides cached config reload with last-known-good fallback."""

    def __init__(self, loader: ConfigLoader) -> None:
        self.loader = loader
        self._active_config: ActiveConfig | None = None
        self._active_pricing: PricingConfig | None = None
        self._tracked_mtimes: tuple[float, float | None] | None = None

    def get_current(self) -> tuple[ActiveConfig, PricingConfig]:
        """Return the current valid config bundle, reloading if files changed."""
        if self._active_config is None or self._active_pricing is None:
            self._reload_or_raise()
            return self._active_config, self._active_pricing

        current_mtimes = self._get_tracked_mtimes()
        if current_mtimes != self._tracked_mtimes:
            self._reload_if_valid()

        return self._active_config, self._active_pricing

    def _reload_or_raise(self) -> None:
        config, pricing = self._load_bundle()
        self._active_config = config
        self._active_pricing = pricing
        self._tracked_mtimes = self._get_tracked_mtimes()

    def _reload_if_valid(self) -> None:
        try:
            config, pricing = self._load_bundle()
        except (FileNotFoundError, ValueError):
            return

        self._active_config = config
        self._active_pricing = pricing
        self._tracked_mtimes = self._get_tracked_mtimes()

    def _load_bundle(self) -> tuple[ActiveConfig, PricingConfig]:
        return self.loader.load(), self.loader.load_pricing()

    def _get_tracked_mtimes(self) -> tuple[float, float | None]:
        pricing_mtime = None
        if self.loader.pricing_path is not None:
            pricing_mtime = self.loader.pricing_path.stat().st_mtime

        return (self.loader.config_path.stat().st_mtime, pricing_mtime)
