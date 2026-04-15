from __future__ import annotations

import unittest


class UITests(unittest.TestCase):
    def test_streamlit_entrypoint_imports(self) -> None:
        from ui import app

        self.assertTrue(callable(app.run_app))


if __name__ == "__main__":
    unittest.main()
