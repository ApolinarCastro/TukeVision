"""Tests for Source Security State (Slice 10)."""

import pytest
from src.security.source import SourceSecurityManager, SecurityEvent, TrustLevel

def test_source_security_lifecycle():
    sec = SourceSecurityManager(suspicion_threshold=10.0, compromised_threshold=30.0)
    cam_id = "cam_front_01"
    
    # Starts HIGH
    assert sec.get_trust_level(cam_id) == TrustLevel.HIGH
    
    # 1. Minor frame drops
    for _ in range(5):
        sec.report_event(cam_id, SecurityEvent.FRAME_DROP)
        
    # Score = 5.0 -> Still HIGH
    assert sec.get_trust_level(cam_id) == TrustLevel.HIGH
    
    # 2. Timestamp mismatch (adds 5.0 -> total 10.0) -> SUSPICIOUS
    sec.report_event(cam_id, SecurityEvent.TIMESTAMP_MISMATCH)
    assert sec.get_trust_level(cam_id) == TrustLevel.SUSPICIOUS
    
    # 3. Major tampering (Unexpected metadata, adds 10.0 -> 20.0, still Suspicious)
    sec.report_event(cam_id, SecurityEvent.UNEXPECTED_METADATA)
    assert sec.get_trust_level(cam_id) == TrustLevel.SUSPICIOUS
    
    # 4. Another tampering -> 30.0 -> COMPROMISED
    sec.report_event(cam_id, SecurityEvent.UNEXPECTED_METADATA)
    assert sec.get_trust_level(cam_id) == TrustLevel.COMPROMISED
    
    # 5. Recovery mechanism
    sec.recover_trust(cam_id, amount=15.0)
    # Score -> 15.0 -> Back to SUSPICIOUS
    assert sec.get_trust_level(cam_id) == TrustLevel.SUSPICIOUS
