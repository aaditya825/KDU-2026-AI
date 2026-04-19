import os
from pathlib import Path
import shutil
import time
from uuid import uuid4

import pytest

from src.config_loader.config_loader import ConfigLoader, ConfigManager


def test_config_loader_loads_active_config() -> None:
    loader = ConfigLoader(
        config_path=Path("configs/config.yaml"),
        pricing_path=Path("configs/pricing.yaml"),
    )

    active_config = loader.load()

    assert active_config.app.name == "fixit-llmops"
    assert active_config.classifier.mode == "rule_based"
    assert active_config.models.default_tier == "economy"
    assert len(active_config.routing.rules) == 3


def test_config_loader_loads_pricing() -> None:
    loader = ConfigLoader(
        config_path=Path("configs/config.yaml"),
        pricing_path=Path("configs/pricing.yaml"),
    )

    pricing = loader.load_pricing()

    assert "gemini" in pricing.providers
    assert "gemini-2.5-flash-lite" in pricing.providers["gemini"].models


def test_config_loader_raises_for_missing_file() -> None:
    missing_path = Path("configs/does-not-exist.yaml")
    loader = ConfigLoader(config_path=missing_path)

    with pytest.raises(FileNotFoundError):
        loader.load()


def test_config_manager_reloads_valid_updated_config() -> None:
    sandbox_dir = Path.cwd() / f"config-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        config_path = sandbox_dir / "config.yaml"
        pricing_path = sandbox_dir / "pricing.yaml"
        config_path.write_text(Path("configs/config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
        pricing_path.write_text(Path("configs/pricing.yaml").read_text(encoding="utf-8"), encoding="utf-8")

        manager = ConfigManager(ConfigLoader(config_path=config_path, pricing_path=pricing_path))
        active_config, _ = manager.get_current()
        assert active_config.app.entry_mode == "api"

        time.sleep(0.02)
        updated_text = config_path.read_text(encoding="utf-8").replace("entry_mode: api", "entry_mode: cli")
        config_path.write_text(updated_text, encoding="utf-8")
        future_time = time.time() + 1
        os.utime(config_path, (future_time, future_time))

        reloaded_config, _ = manager.get_current()
        assert reloaded_config.app.entry_mode == "cli"
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


def test_config_manager_keeps_last_valid_config_on_invalid_reload() -> None:
    sandbox_dir = Path.cwd() / f"config-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    try:
        config_path = sandbox_dir / "config.yaml"
        pricing_path = sandbox_dir / "pricing.yaml"
        config_path.write_text(Path("configs/config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
        pricing_path.write_text(Path("configs/pricing.yaml").read_text(encoding="utf-8"), encoding="utf-8")

        manager = ConfigManager(ConfigLoader(config_path=config_path, pricing_path=pricing_path))
        active_config, _ = manager.get_current()
        assert active_config.models.default_tier == "economy"

        time.sleep(0.02)
        config_path.write_text("app: invalid", encoding="utf-8")
        future_time = time.time() + 1
        os.utime(config_path, (future_time, future_time))

        fallback_config, _ = manager.get_current()
        assert fallback_config.models.default_tier == "economy"
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)
