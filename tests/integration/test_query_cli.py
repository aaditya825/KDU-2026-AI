import subprocess
import sys


def test_query_cli_accepts_direct_argument() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/query_app.py", "Can I reschedule my cleaning appointment?"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Category: booking" in result.stdout
    assert "Response:" in result.stdout


def test_query_cli_accepts_stdin_input() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/query_app.py"],
        input="What are your hours?\nquit\n",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Interactive FixIt CLI started." in result.stdout
    assert "Category: FAQ" in result.stdout
    assert "Model Tier:" in result.stdout
    assert "Exiting interactive FixIt CLI." in result.stdout


def test_query_cli_handles_multiple_interactive_queries() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/query_app.py"],
        input="What are your hours?\nCan I reschedule my cleaning appointment?\nexit\n",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.count("Query ID:") == 2
    assert "Category: FAQ" in result.stdout
    assert "Category: booking" in result.stdout
