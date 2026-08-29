import uuid
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class InvestigationCandidate:
    candidate_id: str
    situation_type: str
    entity_ids: List[str]
    camera_ids: List[str]
    zone_ids: List[str]
    first_observed_at: float
    last_observed_at: float
    evidence_bundle_ids: List[str]
    source_health: Dict[str, Any]
    observation_state: str
    freshness: float
    confidence: float
    priority_score: str
    priority_reasons: List[str]
    status: str

class AttentionOrchestrator:
    """
    Deterministic layer between Operational State and Agent Monitor.
    Groups, deduplicates, and prioritizes operational events into InvestigationCandidates.
    """
    def __init__(self, deduplication_window_seconds: float = 60.0):
        self._deduplication_window = deduplication_window_seconds
        # Key: (entity_id, zone_id, behavior, situation_type)
        self._active_candidates: Dict[str, InvestigationCandidate] = {}

    def _derive_priority(self, behavior: str, duration: float, zone_sensitivity: str) -> tuple[str, List[str]]:
        reasons = []
        priority = "INFORMATIONAL"
        score = 0
        
        # Simple deterministic rules for priority
        if zone_sensitivity in ("HIGH", "CRITICAL"):
            reasons.append("Sensitive zone detected.")
            score += 2
            
        if duration > 120.0:
            reasons.append("Prolonged presence.")
            score += 1
            
        if behavior in ("loitering", "unauthorized_access"):
            reasons.append(f"Behavior pattern matches '{behavior}'.")
            score += 2
            
        if score == 0:
            priority = "INFORMATIONAL"
        elif score == 1:
            priority = "LOW"
        elif score == 2:
            priority = "MEDIUM"
        elif score == 3:
            priority = "HIGH"
        else:
            priority = "CRITICAL"
            
        if not reasons:
            reasons.append("Routine observation.")
            
        return priority, reasons

    def process_observation(
        self,
        entity_id: str,
        zone_id: str,
        behavior: str,
        situation_type: str,
        camera_id: str,
        timestamp: float,
        zone_sensitivity: str = "NORMAL",
        evidence_bundle_id: Optional[str] = None,
        source_health: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0
    ) -> InvestigationCandidate:
        """
        Processes a raw operational observation and returns an InvestigationCandidate.
        Handles deduplication and state transitioning (NEW -> ACTIVE -> UPDATED).
        """
        dedup_key = f"{entity_id}:{zone_id}:{behavior}:{situation_type}"
        
        if source_health is None:
            source_health = {}
            
        existing = self._active_candidates.get(dedup_key)
        
        if existing and (timestamp - existing.last_observed_at <= self._deduplication_window):
            # Update existing candidate
            if camera_id not in existing.camera_ids:
                existing.camera_ids.append(camera_id)
            if evidence_bundle_id and evidence_bundle_id not in existing.evidence_bundle_ids:
                existing.evidence_bundle_ids.append(evidence_bundle_id)
                
            existing.last_observed_at = timestamp
            existing.freshness = time.time() - timestamp
            
            # Recalculate priority based on new duration
            duration = existing.last_observed_at - existing.first_observed_at
            priority, reasons = self._derive_priority(behavior, duration, zone_sensitivity)
            existing.priority_score = priority
            existing.priority_reasons = reasons
            
            if existing.status == "NEW":
                existing.status = "ACTIVE"
            else:
                existing.status = "UPDATED"
                
            return existing

        # Create new candidate
        duration = 0.0
        priority, reasons = self._derive_priority(behavior, duration, zone_sensitivity)
        
        candidate = InvestigationCandidate(
            candidate_id=uuid.uuid4().hex,
            situation_type=situation_type,
            entity_ids=[entity_id],
            camera_ids=[camera_id],
            zone_ids=[zone_id],
            first_observed_at=timestamp,
            last_observed_at=timestamp,
            evidence_bundle_ids=[evidence_bundle_id] if evidence_bundle_id else [],
            source_health=source_health,
            observation_state="OBSERVED",
            freshness=time.time() - timestamp,
            confidence=confidence,
            priority_score=priority,
            priority_reasons=reasons,
            status="NEW"
        )
        
        self._active_candidates[dedup_key] = candidate
        return candidate
        
    def get_active_candidates(self) -> List[InvestigationCandidate]:
        return list(self._active_candidates.values())

    def expire_candidates(self, current_time: float) -> None:
        """Transitions stale candidates to EXPIRED or RESOLVED."""
        expired_keys = []
        for key, candidate in self._active_candidates.items():
            if current_time - candidate.last_observed_at > self._deduplication_window:
                candidate.status = "EXPIRED"
                expired_keys.append(key)
                
        for key in expired_keys:
            # Depending on retention strategy, we might pop them or keep them for history.
            # We'll just remove them from active tracking for deduplication purposes.
            self._active_candidates.pop(key)
