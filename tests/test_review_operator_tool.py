import csv, json, subprocess, sys, tempfile, unittest
from pathlib import Path

class TestReviewOperatorTool(unittest.TestCase):
    def test_bat_uses_base_venv_and_no_secrets(self):
        text = Path("review_behavior_signals.bat").read_text(encoding="utf-8")
        self.assertIn(".venv\\Scripts\\python.exe", text)
        self.assertNotIn("rtsp://", text.lower()); self.assertNotIn("password", text.lower())
    def test_not_ready_is_clean(self):
        script = Path("scripts/review_behavior_signals.py")
        with tempfile.TemporaryDirectory() as tmp:
            # Import module and point its evidence root at an empty directory.
            import importlib.util
            spec = importlib.util.spec_from_file_location("review_tool", script)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            module.EVIDENCE = Path(tmp)
            self.assertEqual(module.main(), 2)

if __name__ == "__main__": unittest.main()
