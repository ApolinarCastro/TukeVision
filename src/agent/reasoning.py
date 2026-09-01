from typing import List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class InvestigationResult:
    facts: List[str] = field(default_factory=list)
    inferences: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    priority_change: str = "NONE"
    recommended_action: str = "REVIEW"

class ReasoningProviderContract:
    def investigate(self, context: Dict[str, Any]) -> InvestigationResult:
        raise NotImplementedError

class DeterministicReasoner(ReasoningProviderContract):
    """
    A non-LLM reasoner that applies strict if-then rules to generate
    epistemic statements from structured operational state.
    """
    def investigate(self, context: Dict[str, Any]) -> InvestigationResult:
        res = InvestigationResult()
        candidate = context.get("candidate", {})
        
        # Facts extraction
        if candidate.get("entity_ids"):
            res.facts.append(f"Entity {candidate['entity_ids'][0]} observed in {candidate.get('zone_ids', ['unknown'])[0]}.")
        
        duration = candidate.get("last_observed_at", 0) - candidate.get("first_observed_at", 0)
        res.facts.append(f"Observation duration: {duration:.1f} seconds.")
        
        if candidate.get("camera_ids"):
            res.facts.append(f"Observed by cameras: {', '.join(candidate['camera_ids'])}.")
            
        # Inferences
        if duration > 120.0:
            res.inferences.append("Movement pattern suggests prolonged presence, warranting operator review.")
            res.priority_change = "ESCALATED"
        elif candidate.get("situation_type") == "unauthorized_access":
            res.inferences.append("Entity breached restricted zone.")
            res.priority_change = "ESCALATED"
            
        # Unknowns
        res.unknowns.append("Intent of the entity.")
        if not candidate.get("evidence_bundle_ids"):
            res.unknowns.append("Visual evidence not yet bundled.")
            
        res.recommended_action = "Operator review recommended."
        return res

class FakeReasoner(ReasoningProviderContract):
    """
    Used strictly for testing specific anti-hallucination and epistemic paths.
    """
    def __init__(self, predefined_result: InvestigationResult = None):
        self._res = predefined_result or InvestigationResult()
        
    def investigate(self, context: Dict[str, Any]) -> InvestigationResult:
        return self._res
