import unittest
import time
from src.agent.attention_orchestrator import AttentionOrchestrator

class TestAttentionOrchestrator(unittest.TestCase):
    def setUp(self):
        # Window of 60 seconds for deduplication
        self.orchestrator = AttentionOrchestrator(deduplication_window_seconds=60.0)

    def test_candidate_generation_and_priority(self):
        timestamp = time.time()
        
        # Test 1: Routine observation
        candidate = self.orchestrator.process_observation(
            entity_id="E01",
            zone_id="aisle_3",
            behavior="walking",
            situation_type="movement",
            camera_id="cam_01",
            timestamp=timestamp,
            zone_sensitivity="NORMAL"
        )
        
        self.assertEqual(candidate.status, "NEW")
        self.assertEqual(candidate.priority_score, "INFORMATIONAL")
        self.assertIn("Routine observation.", candidate.priority_reasons)
        self.assertEqual(len(candidate.entity_ids), 1)

    def test_candidate_deduplication(self):
        base_time = time.time()
        
        # First observation
        c1 = self.orchestrator.process_observation(
            entity_id="E42",
            zone_id="caja_1",
            behavior="loitering",
            situation_type="suspicious",
            camera_id="cam_07",
            timestamp=base_time,
            zone_sensitivity="HIGH"
        )
        self.assertEqual(c1.status, "NEW")
        self.assertEqual(c1.priority_score, "CRITICAL") # HIGH zone + loitering = 4 => CRITICAL
        
        # Second observation (duplicate, 10 seconds later, different camera)
        c2 = self.orchestrator.process_observation(
            entity_id="E42",
            zone_id="caja_1",
            behavior="loitering",
            situation_type="suspicious",
            camera_id="cam_08",
            timestamp=base_time + 10.0,
            zone_sensitivity="HIGH",
            evidence_bundle_id="EB-882"
        )
        
        self.assertEqual(c1.candidate_id, c2.candidate_id, "Candidate ID should remain the same (deduplicated)")
        self.assertEqual(c2.status, "ACTIVE", "Status should transition to ACTIVE on first deduplication")
        self.assertIn("cam_07", c2.camera_ids)
        self.assertIn("cam_08", c2.camera_ids)
        self.assertIn("EB-882", c2.evidence_bundle_ids)
        
        # Third observation (duplicate, 30 seconds later)
        c3 = self.orchestrator.process_observation(
            entity_id="E42",
            zone_id="caja_1",
            behavior="loitering",
            situation_type="suspicious",
            camera_id="cam_08",
            timestamp=base_time + 30.0,
            zone_sensitivity="HIGH"
        )
        self.assertEqual(c3.status, "UPDATED", "Status should transition to UPDATED on subsequent deduplications")
        self.assertEqual(len(self.orchestrator.get_active_candidates()), 1, "Should only have 1 active candidate, not 3")

    def test_priority_escalation(self):
        base_time = time.time()
        
        # Normal zone, normal behavior
        c = self.orchestrator.process_observation(
            entity_id="E99",
            zone_id="aisle_1",
            behavior="standing",
            situation_type="presence",
            camera_id="cam_01",
            timestamp=base_time,
            zone_sensitivity="NORMAL"
        )
        self.assertEqual(c.priority_score, "INFORMATIONAL")
        
        # Keep it alive every 30 seconds to simulate prolonged presence
        for i in range(1, 6):
            c_temp = self.orchestrator.process_observation(
                entity_id="E99",
                zone_id="aisle_1",
                behavior="standing",
                situation_type="presence",
                camera_id="cam_01",
                timestamp=base_time + (i * 30.0),
                zone_sensitivity="NORMAL"
            )
            
        self.assertEqual(c_temp.priority_score, "LOW")
        self.assertIn("Prolonged presence.", c_temp.priority_reasons)
        
    def test_expiration(self):
        base_time = time.time()
        self.orchestrator.process_observation(
            entity_id="E01", zone_id="Z1", behavior="B1", situation_type="S1",
            camera_id="C1", timestamp=base_time
        )
        
        self.assertEqual(len(self.orchestrator.get_active_candidates()), 1)
        
        # Expire checking at base_time + 120 (past the 60s window)
        self.orchestrator.expire_candidates(base_time + 120.0)
        
        self.assertEqual(len(self.orchestrator.get_active_candidates()), 0)

if __name__ == "__main__":
    unittest.main()
