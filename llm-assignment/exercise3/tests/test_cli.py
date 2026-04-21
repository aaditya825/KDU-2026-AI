from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import Mock, patch

from tri_model_assistant.interface import cli


class CLIInputValidationTests(unittest.TestCase):
    def test_load_input_text_rejects_missing_file(self) -> None:
        missing_path = Mock(spec=Path)
        missing_path.__str__ = Mock(return_value="missing-input.txt")
        missing_path.exists.return_value = False

        with self.assertRaisesRegex(ValueError, "does not exist"):
            cli._load_input_text(missing_path)

    def test_load_input_text_rejects_empty_file(self) -> None:
        input_path = Mock(spec=Path)
        input_path.exists.return_value = True
        input_path.is_file.return_value = True
        input_path.read_text.return_value = "   \n\t"

        with self.assertRaisesRegex(ValueError, "Input document is empty"):
            cli._load_input_text(input_path)


class CLIRuntimeErrorHandlingTests(unittest.TestCase):
    def test_main_returns_error_when_query_processing_fails(self) -> None:
        fake_assistant = type(
            "FakeAssistant",
            (),
            {"handle_query": lambda self, query: (_ for _ in ()).throw(RuntimeError("model load failed"))},
        )()

        stderr = io.StringIO()
        with (
            patch("tri_model_assistant.interface.cli._load_input_text", return_value="Valid source text."),
            patch("tri_model_assistant.interface.cli.QueryRoutedAssistant", return_value=fake_assistant),
            redirect_stderr(stderr),
        ):
            exit_code = cli.main(["--input-file", "source.txt", "--query", "Summarize this document"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Failed to process query: model load failed", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
