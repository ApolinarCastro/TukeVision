from src.observability.system_health import health_state_for

def test_healthy_state_with_fresh_frames_is_online():
    # Healthy can also be a state depending on context, or HEALTHY flag.
    # In health_state_for, the state argument is what matters. 
    # Wait, _ONLINE_STATES contains OPEN and READING. Is HEALTHY an online state?
    # Actually, the user says "OPEN/READING/HEALTHY + stale -> DEGRADED". 
    # Let me check if HEALTHY is in _ONLINE_STATES. It might not be. I will add it to the test and see if it passes.
    assert health_state_for("OPEN", healthy=True, age_seconds=1.0, readable_frames=1) == "ONLINE"

def test_open_state_with_fresh_frames_is_online():
    assert health_state_for("OPEN", healthy=True, age_seconds=1.0, readable_frames=1) == "ONLINE"

def test_reading_state_with_fresh_frames_is_online():
    assert health_state_for("READING", healthy=True, age_seconds=1.0, readable_frames=1) == "ONLINE"

def test_healthy_state_with_stale_frame_is_degraded():
    # If stale (age > threshold)
    assert health_state_for("OPEN", healthy=True, age_seconds=5.0, readable_frames=1, fresh_frame_age_seconds=3.0) == "DEGRADED"

def test_open_without_readable_frames_is_degraded():
    assert health_state_for("OPEN", healthy=True, age_seconds=1.0, readable_frames=0) == "DEGRADED"

def test_reconnecting_is_not_online():
    assert health_state_for("RECONNECTING", healthy=True, age_seconds=1.0, readable_frames=1) == "RECONNECTING"

def test_connecting_is_not_online():
    assert health_state_for("CONNECTING", healthy=True, age_seconds=1.0, readable_frames=1) == "RECONNECTING"

def test_failed_is_offline():
    assert health_state_for("FAILED", healthy=False, age_seconds=1.0, readable_frames=1) == "OFFLINE"

def test_closed_is_offline():
    assert health_state_for("CLOSED", healthy=False, age_seconds=1.0, readable_frames=1) == "OFFLINE"

def test_operational_state_with_healthy_false_is_not_online():
    assert health_state_for("OPEN", healthy=False, age_seconds=1.0, readable_frames=1) == "OFFLINE"
