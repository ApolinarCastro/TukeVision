import unittest
from pathlib import Path
import re


class TestTkMulticameraRenderer(unittest.TestCase):
    def test_renderer_is_config_driven_and_owns_no_capture(self):
        source = Path("src/ui/tk_view.py").read_text(encoding="utf-8")
        self.assertIn("grid_layout", source)
        self.assertIn("poll_multicamera", source)
        self.assertNotIn("VideoCapture", source)
        self.assertNotIn("PANEL_LAYOUT", source)
        # Should use config-driven camera set, not hardcoded array of CAM-001..CAM-004
        # Check for hardcoded tuple/list of the 4 legacy cameras together
        source_no_docs = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
        source_no_docs = re.sub(r"#.*", "", source_no_docs)
        # Pattern for hardcoded 4-camera tuple/list
        four_camera_pattern = re.compile(
            r'[(\[]\s*["\']CAM-001["\']\s*,\s*["\']CAM-002["\']\s*,\s*["\']CAM-003["\']\s*,\s*["\']CAM-004["\']\s*[)\]]'
        )
        self.assertIsNone(four_camera_pattern.search(source_no_docs))

    def test_view_model_has_no_fixed_four_camera_mapping(self):
        source = Path("src/ui/multicamera.py").read_text(encoding="utf-8")
        # Remove docstrings/comments before checking
        source_no_docs = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
        source_no_docs = re.sub(r"#.*", "", source_no_docs)
        # Pattern for hardcoded 4-camera tuple/list
        four_camera_pattern = re.compile(
            r'[(\[]\s*["\']CAM-001["\']\s*,\s*["\']CAM-002["\']\s*,\s*["\']CAM-003["\']\s*,\s*["\']CAM-004["\']\s*[)\]]'
        )
        self.assertIsNone(four_camera_pattern.search(source_no_docs))
        self.assertIn("camera_ids", source)
        self.assertIn("grid_layout", source)


if __name__ == "__main__":
    unittest.main()