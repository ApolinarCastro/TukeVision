import logging
from src.agent.reasoning import InvestigationResult

logger = logging.getLogger("agent_validator")

class AgentOutputValidator:
    """
    Validates LLM/VLM outputs for epistemic safety and anti-hallucination rules.
    """
    def __init__(self, max_unsupported_facts_before_fallback: int = 0):
        self.max_unsupported = max_unsupported_facts_before_fallback

    def validate(self, result: InvestigationResult, context: dict) -> InvestigationResult:
        validated = InvestigationResult(
            facts=[],
            inferences=result.inferences.copy(),
            unknowns=result.unknowns.copy(),
            priority_change=result.priority_change,
            recommended_action=result.recommended_action
        )
        
        candidate = context.get("candidate", {})
        allowed_entities = set(candidate.get("entity_ids", []))
        allowed_cameras = set(candidate.get("camera_ids", []))
        allowed_zones = set(candidate.get("zone_ids", []))
        
        unsupported_count = 0
        
        for fact in result.facts:
            # Very basic mock validation logic for the pipeline demonstration
            # In a real scenario, this would use strict NLP/Schema checks or small regexes
            is_supported = True
            
            # If the fact mentions an entity NOT in the candidate, it's hallucinated
            if "Entity" in fact:
                mentioned_entities = [e for e in allowed_entities if e in fact]
                if not mentioned_entities and any(f"E{i}" in fact for i in range(100)):
                    is_supported = False
            
            # If the fact mentions a camera NOT in the candidate
            if "cam_" in fact:
                mentioned_cams = [c for c in allowed_cameras if c in fact]
                if not mentioned_cams:
                    is_supported = False
                    
            if is_supported:
                validated.facts.append(fact)
            else:
                unsupported_count += 1
                logger.warning(f"Rejecting unsupported fact: {fact}")
                # Degrade to unknown
                validated.unknowns.append(f"Verification failed for claim: {fact}")
                
        if unsupported_count > self.max_unsupported:
            raise ValueError(f"Output rejected due to {unsupported_count} unsupported facts.")
            
        return validated
