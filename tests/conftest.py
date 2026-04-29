from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest


@pytest.fixture
def local_tmp_path() -> Path:
    root = Path("tests/.tmp")
    root.mkdir(parents=True, exist_ok=True)
    path = root / str(uuid.uuid4())
    path.mkdir(parents=True, exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)
