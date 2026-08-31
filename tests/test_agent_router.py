import unittest
from src.agent.router import ReasoningRouter
from src.agent.reasoning import DeterministicReasoner, FakeReasoner, InvestigationResult
from src.agent.budget import ReasoningBudget
from src.agent.validator import AgentOutputValidator

class TestReasoningRouter(unittest.TestCase):
    def setUp(self):
        self.det = DeterministicReasoner()
        
        # Fake LLM that returns a hallucinated entity
        self.llm = FakeReasoner(InvestigationResult(facts=["Entity E99 is angry."]))
        
        # Fake VLM that works correctly
        self.vlm = FakeReasoner(InvestigationResult(facts=["Entity E01 is carrying a box."]))
        
        self.validator = AgentOutputValidator()
        self.budget = ReasoningBudget(force_state="NORMAL")
        
        self.router = ReasoningRouter(self.det, self.llm, self.vlm, self.budget, self.validator)

    def test_case_a_deterministic_only(self):
        context = {"candidate": {"situation_type": "movement", "entity_ids": ["E01"]}}
        result = self.router.route(context)
        
        # Should stay deterministic because structured is sufficient
        self.assertTrue(any("E01" in f for f in result.facts))
        self.assertFalse(any("E99" in f for f in result.facts))

    def test_case_b_llm_escalation_and_fallback(self):
        # Force complex correlation to trigger LLM
        context = {"candidate": {"situation_type": "complex_correlation", "entity_ids": ["E01"]}}
        
        # LLM returns E99 which is hallucinated (E99 not in candidate entity_ids).
        # Validator will reject and throw exception -> Router catches and falls back to deterministic.
        result = self.router.route(context)
        
        # Since fallback happened, result should be from DeterministicReasoner
        self.assertTrue(any("E01" in f for f in result.facts), f"Expected E01, got: {result.facts}")

    def test_case_c_vlm_escalation(self):
        context = {"candidate": {"situation_type": "visual_ambiguity", "entity_ids": ["E01"]}}
        
        # VLM returns E01 carrying a box, which is supported because E01 is allowed
        # (Though we mock the VLM, let's just make the LLM also return valid things to let it pass through to VLM)
        
        valid_llm = FakeReasoner(InvestigationResult(facts=["Entity E01 moved."]))
        router2 = ReasoningRouter(self.det, valid_llm, self.vlm, self.budget, self.validator)
        
        result = router2.route(context)
        
        # Should hit VLM
        self.assertTrue(any("box" in f for f in result.facts), f"Expected box, got: {result.facts}")

    def test_case_e_critical_budget(self):
        # If queue depth is massive, budget goes CRITICAL, forces deterministic
        context = {"candidate": {"situation_type": "visual_ambiguity", "entity_ids": ["E01"]}}
        
        # Override budget without force_state to allow queue_depth to trigger CRITICAL
        router = ReasoningRouter(self.det, self.llm, self.vlm, ReasoningBudget(), self.validator)
        
        # High queue depth forces CRITICAL
        result = router.route(context, queue_depth=100)
        
        # Should NOT reach VLM
        self.assertFalse(any("box" in f for f in result.facts))

if __name__ == "__main__":
    unittest.main()
