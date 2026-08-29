import unittest
import time
from src.agent.attention_orchestrator import InvestigationCandidate
from src.agent.correlation import CorrelationEngine

class TestAgentCorrelation(unittest.TestCase):
    def test_source_health_awareness(self):
        def mock_scene_state():
            return {"entities": {"E01": {"previous_zone": "hallway"}}}
            
        def mock_camera_health(cam_id):
            if cam_id == "cam_04":
                return {"status": "DEGRADED", "reason": "Drop Frame Injection detected."}
            return {"status": "OK"}
            
        engine = CorrelationEngine(mock_scene_state, mock_camera_health)
        
        candidate = InvestigationCandidate(
            candidate_id="C1",
            situation_type="movement",
            entity_ids=["E01"],
            camera_ids=["cam_03", "cam_04"],
            zone_ids=["secure_zone"],
            first_observed_at=time.time(),
            last_observed_at=time.time(),
            evidence_bundle_ids=[],
            source_health={},
            observation_state="OBSERVED",
            freshness=0.1,
            confidence=0.9,
            priority_score="MEDIUM",
            priority_reasons=[],
            status="ACTIVE"
        )
        
        context = engine.correlate(candidate)
        
        # Check source health awareness
        self.assertEqual(context["source_health"]["cam_03"]["status"], "OK")
        self.assertEqual(context["source_health"]["cam_04"]["status"], "DEGRADED")
        
        # Check that a temporal correlation warning was injected
        self.assertTrue(any("cam_04 is degraded" in w for w in context["temporal_correlations"]))
        
        # Check spatial correlation inference
        self.assertTrue(any("moved from hallway to secure_zone" in s for s in context["spatial_correlations"]))

if __name__ == "__main__":
    unittest.main()
