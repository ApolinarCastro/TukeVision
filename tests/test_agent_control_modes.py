import unittest
import time
from src.agent.control import AgentControlConfig, AgentController
from src.agent.monitor import AgentMonitor
from src.agent.reasoning import DeterministicReasoner
from src.agent.audit import AgentAuditLog
from src.agent.attention_orchestrator import InvestigationCandidate

class TestAgentControlModes(unittest.TestCase):
    def setUp(self):
        self.audit = AgentAuditLog("data/test_audit.jsonl")
        self.reasoner = DeterministicReasoner()
        self.monitor = AgentMonitor(self.reasoner, self.audit)
        
        self.candidate = InvestigationCandidate(
            candidate_id="C_CONTROL",
            situation_type="test",
            entity_ids=["E01"],
            camera_ids=["cam_01"],
            zone_ids=["Z1"],
            first_observed_at=time.time(),
            last_observed_at=time.time(),
            evidence_bundle_ids=[],
            source_health={},
            observation_state="OBSERVED",
            freshness=0.1,
            confidence=1.0,
            priority_score="LOW",
            priority_reasons=[],
            status="NEW"
        )

    def test_kill_switch(self):
        config = AgentControlConfig(enabled=False)
        controller = AgentController(self.monitor, config)
        
        # When disabled, investigate returns None
        result = controller.investigate(self.candidate)
        self.assertIsNone(result)
        
        # Re-enable
        config.set_enabled(True)
        result2 = controller.investigate(self.candidate)
        self.assertIsNotNone(result2)

    def test_safe_mode(self):
        config = AgentControlConfig(enabled=True, mode="SAFE")
        controller = AgentController(self.monitor, config)
        
        self.assertTrue(config.is_safe_mode)
        
        # Should still run successfully since DeterministicReasoner is safe.
        result = controller.investigate(self.candidate)
        self.assertIsNotNone(result)

if __name__ == "__main__":
    unittest.main()
