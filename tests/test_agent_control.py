import unittest
from src.agent.tool_policy import AgentToolPolicy

class TestAgentControl(unittest.TestCase):
    def setUp(self):
        self.policy = AgentToolPolicy()

    def test_tool_allowlist(self):
        # Explicitly allowed
        self.assertTrue(self.policy.is_tool_allowed("get_scene_state"))
        self.assertTrue(self.policy.is_tool_allowed("get_evidence_bundle"))
        
        # Explicitly denied / not in list
        self.assertFalse(self.policy.is_tool_allowed("delete_evidence"))
        self.assertFalse(self.policy.is_tool_allowed("execute_shell"))
        self.assertFalse(self.policy.is_tool_allowed("set_camera_password"))

    def test_argument_sanitization(self):
        args = {
            "camera_id": "cam_04",
            "password": "supersecretpassword",
            "url": "rtsp://admin:12345@192.168.1.100/stream"
        }
        
        sanitized = self.policy.sanitize_arguments(args)
        
        self.assertEqual(sanitized["camera_id"], "cam_04")
        self.assertEqual(sanitized["password"], "***REDACTED***")
        self.assertEqual(sanitized["url"], "rtsp://***:***@192.168.1.100/stream")

if __name__ == "__main__":
    unittest.main()
