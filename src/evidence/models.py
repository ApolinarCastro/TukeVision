"""Modelos de evidencia con compatibilidad ONVIF Media Signing.

La evidencia respalda una observación o evento de forma inmutable y con
trazabilidad criptográfica de origen y procedencia.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


class MediaSigningStatus:
    SOURCE_UNSIGNED = "SOURCE_UNSIGNED"
    SIGNED_UNVERIFIED = "SIGNED_UNVERIFIED"
    SIGNED_VALID = "SIGNED_VALID"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    SIGNATURE_UNSUPPORTED = "SIGNATURE_UNSUPPORTED"


@dataclass(frozen=True)
class EvidenceMetadata:
    """Metadatos inmutables asociados a una evidencia."""
    alert_id: str
    event_id: str
    observation_ids: Tuple[str, ...]
    track_id: int
    zone_id: str
    duration_seconds: float
    risk_score: int
    rule_id: str
    timestamp: str
    frame_sha256: str
    # ONVIF Media Signing Contract Readiness (P0)
    signing_status: str = MediaSigningStatus.SOURCE_UNSIGNED
    signature_scheme: Optional[str] = None
    source_identity: Optional[str] = None
    verification_status: str = "NOT_APPLICABLE"
    verification_time: Optional[str] = None
    certificate_chain: Tuple[str, ...] = ()
    original_signature_metadata: Optional[Dict[str, Any]] = None
    media_hash: Optional[str] = None
    provenance_chain: Tuple[str, ...] = ()
