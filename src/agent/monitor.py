import time
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from src.agent.attention_orchestrator import InvestigationCandidate
from src.agent.reasoning import ReasoningProviderContract
from src.agent.audit import AgentAuditLog

@dataclass
class InvestigationSession:
    investigation_id: str
    candidate_id: str
    started_at: float
    updated_at: float
    questions: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    evidence_consulted: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    facts: List[str] = field(default_factory=list)
    inferences: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    correlations: List[str] = field(default_factory=list)
    priority: str = "INFORMATIONAL"
    recommended_operator_attention: str = "REVIEW"
    status: str = "OPEN"

class AgentMonitor:
    def __init__(self, reasoner: ReasoningProviderContract, audit_log: AgentAuditLog):
        self.reasoner = reasoner
        self.audit_log = audit_log
        self._active_sessions: Dict[str, InvestigationSession] = {}
        
    def investigate(self, candidate: InvestigationCandidate) -> InvestigationSession:
        """
        Creates an investigation session and runs the reasoning engine on a candidate.
        """
        session_id = uuid.uuid4().hex
        now = time.time()
        session = InvestigationSession(
            investigation_id=session_id,
            candidate_id=candidate.candidate_id,
            started_at=now,
            updated_at=now,
            priority=candidate.priority_score,
            evidence_consulted=candidate.evidence_bundle_ids.copy()
        )
        
        # Context building
        context = {
            "candidate": {
                "candidate_id": candidate.candidate_id,
                "situation_type": candidate.situation_type,
                "entity_ids": candidate.entity_ids,
                "camera_ids": candidate.camera_ids,
                "zone_ids": candidate.zone_ids,
                "first_observed_at": candidate.first_observed_at,
                "last_observed_at": candidate.last_observed_at,
                "evidence_bundle_ids": candidate.evidence_bundle_ids,
                "source_health": candidate.source_health,
                "priority_score": candidate.priority_score,
            }
        }
        
        t0 = time.time()
        result = self.reasoner.investigate(context)
        t1 = time.time()
        
        # Update Session with Epistemic outputs
        session.facts.extend(result.facts)
        session.inferences.extend(result.inferences)
        session.unknowns.extend(result.unknowns)
        session.recommended_operator_attention = result.recommended_action
        
        if result.priority_change == "ESCALATED":
            # Very naive deterministic escalation for testing
            if session.priority == "INFORMATIONAL": session.priority = "LOW"
            elif session.priority == "LOW": session.priority = "MEDIUM"
            elif session.priority == "MEDIUM": session.priority = "HIGH"
            elif session.priority == "HIGH": session.priority = "CRITICAL"
            
        session.updated_at = time.time()
        session.status = "COMPLETED"
        
        # Audit
        self.audit_log.record_investigation_step(
            investigation_id=session_id,
            candidate_id=candidate.candidate_id,
            tool="ReasoningProvider",
            args={"candidate_id": candidate.candidate_id},
            result_reference="Result",
            facts_generated=result.facts,
            inferences_generated=result.inferences,
            priority_change=result.priority_change,
            duration=t1 - t0
        )
        
        self._active_sessions[session_id] = session
        return session
