import unittest
from src.agent.evidence_selector import EvidenceSelector

class TestEvidenceSelector(unittest.TestCase):
    def test_visual_ambiguity_roi(self):
        selector = EvidenceSelector(max_frames=3)
        context = {
            "candidate": {"situation_type": "visual_ambiguity"},
            "evidence_bundle": {"frames": ["f1", "f2", "f3", "f4"]}
        }
        
        sel = selector.select_for_investigation(context)
        self.assertEqual(sel["frames_considered"], 4)
        self.assertEqual(sel["frames_selected"], 3)
        self.assertTrue(sel["roi_selected"])
        self.assertEqual(len(sel["selected_frames"]), 3)

    def test_normal_keyframe(self):
        selector = EvidenceSelector()
        context = {
            "candidate": {"situation_type": "movement"},
            "evidence_bundle": {"frames": ["f1", "f2"]}
        }
        
        sel = selector.select_for_investigation(context)
        self.assertEqual(sel["frames_considered"], 2)
        self.assertEqual(sel["frames_selected"], 1)
        self.assertFalse(sel["roi_selected"])

    def test_no_evidence(self):
        selector = EvidenceSelector()
        context = {}
        sel = selector.select_for_investigation(context)
        self.assertEqual(sel["frames_considered"], 0)
        self.assertEqual(sel["frames_selected"], 0)

if __name__ == "__main__":
    unittest.main()
