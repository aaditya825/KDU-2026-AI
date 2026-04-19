import os
import shutil
from pathlib import Path
from uuid import uuid4

from src.core.env import load_dotenv


def test_load_dotenv_sets_missing_values_only() -> None:
    sandbox_dir = Path.cwd() / f"env-loader-test-{uuid4().hex}"
    sandbox_dir.mkdir(parents=True, exist_ok=False)
    original_provider_mode = os.environ.get("PROVIDER_MODE")
    try:
        dotenv_path = sandbox_dir / ".env"
        dotenv_path.write_text("PROVIDER_MODE=gemini\nTEST_ENV_VALUE=loaded\n", encoding="utf-8")
        os.environ["PROVIDER_MODE"] = "mock"
        os.environ.pop("TEST_ENV_VALUE", None)

        load_dotenv(dotenv_path)

        assert os.environ["PROVIDER_MODE"] == "mock"
        assert os.environ["TEST_ENV_VALUE"] == "loaded"
    finally:
        if original_provider_mode is None:
            os.environ.pop("PROVIDER_MODE", None)
        else:
            os.environ["PROVIDER_MODE"] = original_provider_mode
        os.environ.pop("TEST_ENV_VALUE", None)
        shutil.rmtree(sandbox_dir, ignore_errors=True)
