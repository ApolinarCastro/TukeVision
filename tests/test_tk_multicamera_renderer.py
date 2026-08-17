import unittest
from pathlib import Path


class TestTkMulticameraRenderer(unittest.TestCase):
    def test_fixed_slots_and_no_direct_capture(self):
        source = Path("src/ui/tk_view.py").read_text(encoding="utf-8")
        self.assertIn("PANEL_LAYOUT", source)
        self.assertIn("poll_multicamera", source)
        self.assertNotIn("VideoCapture", source)
        self.assertNotIn("VideoCapture", source)

    def test_four_panel_mapping_is_explicit(self):
        source = Path("src/ui/multicamera.py").read_text(encoding="utf-8")
        for camera_id in ("CAM-001", "CAM-002", "CAM-003", "CAM-004"):
            self.assertIn(camera_id, source)


if __name__ == "__main__":
    unittest.main()
