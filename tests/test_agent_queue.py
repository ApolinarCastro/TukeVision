import unittest
import time
from src.agent.attention_queue import AttentionQueue, AttentionQueueItem
from src.agent.monitor import InvestigationSession

class TestAgentQueue(unittest.TestCase):
    def test_queue_sorting(self):
        queue = AttentionQueue()
        
        # Low priority session
        s1 = InvestigationSession(
            investigation_id="I1",
            candidate_id="C1",
            started_at=time.time(),
            updated_at=time.time() - 100,
            priority="LOW"
        )
        
        # High priority session
        s2 = InvestigationSession(
            investigation_id="I2",
            candidate_id="C2",
            started_at=time.time(),
            updated_at=time.time(),
            priority="HIGH"
        )
        
        # Informational
        s3 = InvestigationSession(
            investigation_id="I3",
            candidate_id="C3",
            started_at=time.time(),
            updated_at=time.time(),
            priority="INFORMATIONAL"
        )
        
        queue.add_or_update(s1)
        queue.add_or_update(s2)
        queue.add_or_update(s3)
        
        sorted_items = queue.get_sorted_queue()
        
        self.assertEqual(len(sorted_items), 3)
        # Should be High, Low, Informational
        self.assertEqual(sorted_items[0].priority, "HIGH")
        self.assertEqual(sorted_items[1].priority, "LOW")
        self.assertEqual(sorted_items[2].priority, "INFORMATIONAL")

if __name__ == "__main__":
    unittest.main()
