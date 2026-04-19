import subprocess
import sys


def test_local_entrypoint_runs() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_local.py"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Processed query" in result.stdout
