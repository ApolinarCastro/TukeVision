import logging
from src.agent.experience.contract import ReauditCandidate, ExperienceRecord
from src.agent.experience.service import ExperienceService

logger = logging.getLogger("selective_reaudit")

class SelectiveReauditEngine:
    def __init__(self, service: ExperienceService):
        self.service = service
        
    def handle_new_experience(self, trigger_type: str, experience: ExperienceRecord):
        # Only certain triggers cause reaudit
        valid_triggers = [
            "NEW_CORRECTION", "NEW_OUTCOME", "NEW_BENCHMARK",
            "NEW_FAILURE", "NEW_ROOT_CAUSE", "NEW_TECHNOLOGY_EVIDENCE",
            "CONTRADICTORY_EXPERIENCE"
        ]
        if trigger_type not in valid_triggers:
            return
            
        logger.info(f"Trigger {trigger_type} for experience {experience.experience_id}")
        
        # Selective Match
        # In real life this would query components, patterns and find intersections
        related = self.service.find_related_experiences(
            situation_type=experience.pattern,
            component=experience.tukevision_component
        )
        
        affected_ids = [r.experience_id for r in related if r.experience_id != experience.experience_id]
        if not affected_ids:
            logger.info("No affected experiences found. No reaudit needed.")
            return
            
        candidate = ReauditCandidate(
            reaudit_id=f"REAUDIT-{experience.experience_id}",
            trigger_type=trigger_type,
            trigger_experience_id=experience.experience_id,
            affected_experience_ids=affected_ids,
            affected_components=[experience.tukevision_component] if experience.tukevision_component != "UNKNOWN" else [],
            affected_patterns=[experience.pattern] if experience.pattern != "UNKNOWN" else [],
            affected_decisions=[],
            reason=f"New experience {experience.experience_id} modifies knowledge about {experience.pattern}",
            severity="MEDIUM",
            created_at=experience.created_at,
            status="OPEN"
        )
        
        self.service.create_reaudit_candidate(candidate)
        logger.info(f"Reaudit candidate {candidate.reaudit_id} created.")
