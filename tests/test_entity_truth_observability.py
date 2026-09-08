import pytest
import os
import json
import time
from unittest.mock import patch, MagicMock
from src.observability.entity_truth_tracer import emit_entity_truth_trace, _last_emitted_states

@pytest.fixture(autouse=True)
def reset_tracer():
    # Setup
    _last_emitted_states.clear()
    import src.observability.entity_truth_tracer as tracer
    original_enabled = tracer._tracer_enabled
    tracer._tracer_enabled = True
    
    yield
    
    # Teardown
    tracer._tracer_enabled = original_enabled
    _last_emitted_states.clear()

def test_trace_disabled_by_default(monkeypatch):
    monkeypatch.delenv("TUKEVISION_ENTITY_TRACE", raising=False)
    
    # Force reload of _tracer_enabled conceptually or just simulate the state
    import src.observability.entity_truth_tracer as tracer
    tracer._tracer_enabled = os.environ.get("TUKEVISION_ENTITY_TRACE", "0") == "1"
    
    with patch("src.observability.entity_truth_tracer._logger.info") as mock_info:
        emit_entity_truth_trace("CHAIN", "cam_01")
        mock_info.assert_not_called()

def test_trace_enabled_explicitly(monkeypatch):
    monkeypatch.setenv("TUKEVISION_ENTITY_TRACE", "1")
    
    import src.observability.entity_truth_tracer as tracer
    tracer._tracer_enabled = True
    
    with patch("src.observability.entity_truth_tracer._logger.info") as mock_info:
        emit_entity_truth_trace("CHAIN", "cam_01", visit_id="VIS-1")
        mock_info.assert_called_once()
        payload = json.loads(mock_info.call_args[0][0])
        assert payload["trace"] == "ENTITY_TRUTH_TRACE"
        assert payload["boundary"] == "CHAIN"
        assert payload["visit_id"] == "VIS-1"

def test_trace_emits_no_image_data():
    with patch("src.observability.entity_truth_tracer._logger.info") as mock_info:
        emit_entity_truth_trace("CHAIN", "cam_01", visit_id="VIS-1")
        payload = json.loads(mock_info.call_args[0][0])
        
        # Verify no image or frame is in payload
        for key in payload:
            assert "frame" not in key or key == "frame_index"
            assert "image" not in key

def test_trace_preserves_semantic_values():
    with patch("src.observability.entity_truth_tracer._logger.info") as mock_info:
        emit_entity_truth_trace(
            boundary="CONTROLLER", 
            camera_id="cam_01",
            semantic_track_id="TRK-1",
            visit_id="VIS-2",
            visit_role="STAFF",
            person_state="PERSON_STATIONARY"
        )
        
        payload = json.loads(mock_info.call_args[0][0])
        assert payload["boundary"] == "CONTROLLER"
        assert payload["semantic_track_id"] == "TRK-1"
        assert payload["visit_id"] == "VIS-2"
        assert payload["visit_role"] == "STAFF"
        assert payload["person_state"] == "PERSON_STATIONARY"

def test_trace_bounded_deduplicated():
    with patch("src.observability.entity_truth_tracer._logger.info") as mock_info:
        # First emit goes through
        emit_entity_truth_trace("CHAIN", "cam_01", visit_id="VIS-1")
        assert mock_info.call_count == 1
        
        # Second identical emit within 5s is dropped
        emit_entity_truth_trace("CHAIN", "cam_01", visit_id="VIS-1")
        assert mock_info.call_count == 1
        
        # Change in state goes through
        emit_entity_truth_trace("CHAIN", "cam_01", visit_id="VIS-2")
        assert mock_info.call_count == 2
