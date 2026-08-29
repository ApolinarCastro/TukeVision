import unittest
import time
from src.agent.attention_orchestrator import InvestigationCandidate
from src.agent.reasoning import DeterministicReasoner, FakeReasoner, InvestigationResult
from src.agent.audit import AgentAuditLog
from src.agent.monitor import AgentMonitor

class TestAgentEpistemics(unittest.TestCase):
    def setUp(self):
        self.audit = AgentAuditLog(log_path="data/test_audit.jsonl")
        self.reasoner = DeterministicReasoner()
        self.monitor = AgentMonitor(self.reasoner, self.audit)

    def test_fact_inference_separation(self):
        candidate = InvestigationCandidate(
            candidate_id="C123",
            situation_type="unauthorized_access",
            entity_ids=["E01"],
            camera_ids=["cam_05"],
            zone_ids=["secure_zone"],
            first_observed_at=time.time() - 150.0,
            last_observed_at=time.time(),
            evidence_bundle_ids=["EB-999"],
            source_health={"cam_05": "OK"},
            observation_state="OBSERVED",
            freshness=0.1,
            confidence=0.9,
            priority_score="MEDIUM",
            priority_reasons=["Sensitive zone."],
            status="ACTIVE"
        )
        
        session = self.monitor.investigate(candidate)
        
        # Check Epistemic Separation
        self.assertTrue(any("Entity E01" in f for f in session.facts), "Must contain explicit Fact about Entity.")
        self.assertTrue(any("breach" in i.lower() or "prolonged" in i.lower() for i in session.inferences), "Must contain an Inference.")
        self.assertTrue(any("Intent" in u for u in session.unknowns), "Must contain Unknowns.")
        
        # Test Escalation
        self.assertEqual(session.priority, "HIGH", "Medium should have escalated to High.")

    def test_anti_hallucination_with_fake_reasoner(self):
        # FakeReasoner used strictly to test anti-hallucination
        fake_result = InvestigationResult(
            facts=["Entity E02 detected."],
            inferences=["Might be suspicious."],
            unknowns=["Identity is UNKNOWN", "Missing visual evidence is UNKNOWN"]
        )
        fake_reasoner = FakeReasoner(predefined_result=fake_result)
        monitor = AgentMonitor(fake_reasoner, self.audit)
        
        candidate = InvestigationCandidate(
            candidate_id="C999",
            situation_type="movement",
            entity_ids=["E02"],
            camera_ids=["cam_01"],
            zone_ids=["hallway"],
            first_observed_at=time.time(),
            last_observed_at=time.time(),
            evidence_bundle_ids=[],
            source_health={},
            observation_state="OBSERVED",
            freshness=0.1,
            confidence=1.0,
            priority_score="INFORMATIONAL",
            priority_reasons=[],
            status="NEW"
        )
        
        session = monitor.investigate(candidate)
        
        self.assertIn("Identity is UNKNOWN", session.unknowns)
        self.assertNotIn("Identity is John Doe", session.facts)
        
if __name__ == "__main__":
    unittest.main()
