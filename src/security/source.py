"""Source Security State (Slice 10).

Monitors camera feeds for potential tampering, spoofing, or degradation
to establish a TrustLevel for spatial intelligence constraints.
"""

from enum import Enum
from typing import Dict, Any, List
import datetime
import logging

logger = logging.getLogger("tukevision.security.source")

class TrustLevel(Enum):
    HIGH = "HIGH"
    SUSPICIOUS = "SUSPICIOUS"
    COMPROMISED = "COMPROMISED"

class SecurityEvent(Enum):
    FRAME_DROP = "FRAME_DROP"
    TIMESTAMP_MISMATCH = "TIMESTAMP_MISMATCH"
    CONNECTION_LOST = "CONNECTION_LOST"
    UNEXPECTED_METADATA = "UNEXPECTED_METADATA"

class SourceSecurityState:
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.trust_level = TrustLevel.HIGH
        self.incident_count = 0
        self.last_incident_time: datetime.datetime = None
        self.suspicion_score = 0.0

class SourceSecurityManager:
    """Manages the security/trust state of source camera feeds."""
    
    def __init__(self, suspicion_threshold: float = 10.0, compromised_threshold: float = 30.0):
        self._states: Dict[str, SourceSecurityState] = {}
        self._suspicion_threshold = suspicion_threshold
        self._compromised_threshold = compromised_threshold
        
        # Define penalties for different events
        self._penalties = {
            SecurityEvent.FRAME_DROP: 1.0,
            SecurityEvent.TIMESTAMP_MISMATCH: 5.0,
            SecurityEvent.CONNECTION_LOST: 2.0,
            SecurityEvent.UNEXPECTED_METADATA: 10.0 # High indicator of spoof/tampering
        }

    def _get_or_create_state(self, camera_id: str) -> SourceSecurityState:
        if camera_id not in self._states:
            self._states[camera_id] = SourceSecurityState(camera_id)
        return self._states[camera_id]

    def report_event(self, camera_id: str, event_type: SecurityEvent, details: str = ""):
        """Report a security-related event on a camera feed."""
        state = self._get_or_create_state(camera_id)
        penalty = self._penalties.get(event_type, 1.0)
        
        state.suspicion_score += penalty
        state.incident_count += 1
        state.last_incident_time = datetime.datetime.now(datetime.timezone.utc)
        
        self._evaluate_trust(state)
        
        logger.warning(
            f"Security event on {camera_id}: {event_type.name}. "
            f"Score: {state.suspicion_score} -> {state.trust_level.name}"
        )

    def _evaluate_trust(self, state: SourceSecurityState):
        """Evaluate and potentially degrade trust based on accumulated score."""
        if state.suspicion_score >= self._compromised_threshold:
            state.trust_level = TrustLevel.COMPROMISED
        elif state.suspicion_score >= self._suspicion_threshold:
            state.trust_level = TrustLevel.SUSPICIOUS
        else:
            state.trust_level = TrustLevel.HIGH

    def get_trust_level(self, camera_id: str) -> TrustLevel:
        return self._get_or_create_state(camera_id).trust_level

    def recover_trust(self, camera_id: str, amount: float = 5.0):
        """Gradually recover trust over time or via explicit admin action."""
        if camera_id in self._states:
            state = self._states[camera_id]
            state.suspicion_score = max(0.0, state.suspicion_score - amount)
            self._evaluate_trust(state)
