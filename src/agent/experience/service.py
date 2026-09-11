import logging
from typing import List, Optional
from src.agent.experience.contract import (
    ExperienceRecord, ExperienceRelation, ReauditCandidate, FailureExperience
)
from src.agent.experience.store import ExperienceStore

logger = logging.getLogger("agent_experience_service")

class ExperienceService:
    def __init__(self, store: ExperienceStore):
        self.store = store
        
    def record_experience(self, record: ExperienceRecord):
        logger.info(f"Recording experience {record.experience_id}")
        self.store.insert_experience(record)
        
    def get_experience(self, experience_id: str) -> Optional[ExperienceRecord]:
        return self.store.get_experience(experience_id)
        
    def find_related_experiences(self, situation_type: str = None, component: str = None) -> List[ExperienceRecord]:
        return self.store.find_related_experiences(situation_type, component)
        
    def record_relation(self, relation: ExperienceRelation):
        logger.info(f"Recording relation {relation.relation_id}: {relation.source_experience_id} -> {relation.target_experience_id}")
        self.store.insert_relation(relation)
        
    def find_known_failure(self, signature: str) -> Optional[FailureExperience]:
        return self.store.find_known_failure(signature)
        
    def create_reaudit_candidate(self, candidate: ReauditCandidate):
        logger.info(f"Creating reaudit candidate {candidate.reaudit_id} for trigger {candidate.trigger_type}")
        self.store.insert_reaudit_candidate(candidate)
        
    def record_failure(self, failure: FailureExperience):
        logger.info(f"Recording failure {failure.failure_id}")
        self.store.insert_failure(failure)
