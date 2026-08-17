import unittest
from pathlib import Path


class TestMulticameraEntrypoint(unittest.TestCase):
    def test_launcher_selects_mode_without_secrets(self):
        launcher = Path("start_tukevision.ps1").read_text(encoding="utf-8")
        entrypoint = Path("scripts/run_multicamera.py").read_text(encoding="utf-8")
        self.assertIn('Mode -ieq "Multicamera"', launcher)
        self.assertIn("run_multicamera.py", launcher)
        self.assertIn("SourceManager", entrypoint)
        self.assertIn("OperationalPipeline", entrypoint)
        self.assertIn("getpass.getpass", entrypoint)
        self.assertNotIn("rtsp://", launcher.lower())
        self.assertNotIn("password=", launcher.lower())
        self.assertNotIn("VideoCapture", entrypoint)


if __name__ == "__main__":
    unittest.main()
