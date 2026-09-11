from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class OperatorOutcome:
    outcome_id: str
    investigation_id: str
    operator_action: str
    operator_assessment: str
    confirmed_facts: List[str] = field(default_factory=list)
    rejected_inferences: List[str] = field(default_factory=list)
    corrections: List[str] = field(default_factory=list)
    outcome_state: str = "UNKNOWN"
    created_at: str = "UNKNOWN"

@dataclass
class CorrectionRecord:
    what_was_wrong: str
    corrected_value: str
    reason: str
    source: str
    evidence: str
    operator_reference: str
    timestamp: str

@dataclass
class ExperienceRecord:
    experience_id: str
    experience_type: str  # OPERATIONAL | ENGINEERING
    problem: str
    source: str
    source_reference: str
    pattern: str
    evidence_refs: List[str] = field(default_factory=list)
    context: str = "UNKNOWN"
    decision: str = "UNKNOWN"
    outcome: str = "UNKNOWN"
    lesson_learned: str = "UNKNOWN"
    benefit: str = "UNKNOWN"
    limitation: str = "UNKNOWN"
    cost: str = "UNKNOWN"
    dependencies: str = "UNKNOWN"
    license: str = "UNKNOWN"
    maturity: str = "OBSERVED"
    tukevision_component: str = "UNKNOWN"
    confidence: str = "UNKNOWN"
    created_at: str = "UNKNOWN"
    updated_at: str = "UNKNOWN"
    status: str = "UNKNOWN"
    revisit_when: str = "UNKNOWN"

@dataclass
class OperationalExperience(ExperienceRecord):
    def __init__(self, **kwargs):
        kwargs["experience_type"] = "OPERATIONAL"
        super().__init__(**kwargs)

@dataclass
class EngineeringExperience(ExperienceRecord):
    def __init__(self, **kwargs):
        kwargs["experience_type"] = "ENGINEERING"
        super().__init__(**kwargs)

@dataclass
class ExperienceRelation:
    relation_id: str
    source_experience_id: str
    relation_type: str
    target_experience_id: str
    evidence_refs: List[str] = field(default_factory=list)
    created_at: str = "UNKNOWN"

@dataclass
class ReauditCandidate:
    reaudit_id: str
    trigger_type: str
    trigger_experience_id: str
    affected_experience_ids: List[str] = field(default_factory=list)
    affected_components: List[str] = field(default_factory=list)
    affected_patterns: List[str] = field(default_factory=list)
    affected_decisions: List[str] = field(default_factory=list)
    reason: str = "UNKNOWN"
    severity: str = "UNKNOWN"
    created_at: str = "UNKNOWN"
    status: str = "OPEN"

@dataclass
class FailureExperience:
    failure_id: str
    component: str
    symptom: str
    detected_at: str
    root_cause: str
    fix_reference: str
    regression_test_reference: str
    result: str
    recurrence_signature: str
    experience_id: str
