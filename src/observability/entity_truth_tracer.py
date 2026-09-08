import os
import json
import time
import logging
import threading
from pathlib import Path

_tracer_enabled = os.environ.get("TUKEVISION_ENTITY_TRACE", "0") == "1"
_last_emitted_states = {}
_lock = threading.Lock()
_logger = logging.getLogger("tukevision.entity_trace")

_log_file = Path("logs/entity_truth_trace.ndjson")
if _tracer_enabled:
    _log_file.parent.mkdir(parents=True, exist_ok=True)

def _get_state_hash(kwargs):
    """Hash the semantic payload to detect changes."""
    return hash((
        kwargs.get("camera_id"),
        kwargs.get("boundary"),
        kwargs.get("raw_track_id"),
        kwargs.get("semantic_track_id"),
        kwargs.get("visit_id"),
        kwargs.get("visit_role"),
        kwargs.get("person_state"),
        kwargs.get("state_live_count"),
        kwargs.get("health_online_camera_count"),
        kwargs.get("rendered_live_count"),
        kwargs.get("total_camera_count"),
        kwargs.get("ui_presented"),
        kwargs.get("event_type"),
        kwargs.get("source_camera_id"),
        kwargs.get("snapshot_camera_id"),
        kwargs.get("viewmodel_target_camera_id")
    ))

def emit_entity_truth_trace(
    boundary: str,
    camera_id: str,
    frame_index: int = 0,
    generation: int = 0,
    raw_track_id: str = None,
    display_track_id: str = None,
    semantic_track_id: str = None,
    event_type: str = None,
    track_object_type: str = None,
    validated_presence: str = None,
    visit_id: str = None,
    visit_role: str = None,
    person_state: str = None,
    customer_analytics_eligible: bool = False,
    ui_presented: bool = None,
    source_camera_id: str = None,
    snapshot_camera_id: str = None,
    viewmodel_target_camera_id: str = None,
    state_live_count: int = None,
    health_online_camera_count: int = None,
    rendered_live_count: int = None,
    total_camera_count: int = None
):
    """
    Emits a structured read-only trace for the entity temporal truth pipeline.
    Deduplicates repeated identical states. Respects max heartbeat (5s) per boundary+camera+track.
    Thread-safe implementation.
    """
    if not _tracer_enabled:
        return

    now = time.time()
    
    # Identify unique stream by boundary + camera + track (if available)
    track_key = raw_track_id or display_track_id or semantic_track_id or "none"
    stream_key = f"{boundary}_{camera_id}_{track_key}"
    
    current_hash = _get_state_hash(locals())
    
    with _lock:
        last_info = _last_emitted_states.get(stream_key)
        if last_info is not None:
            last_hash, last_time = last_info
            if last_hash == current_hash and (now - last_time) < 5.0:
                return  # Throttle unchanged state within 5s

        _last_emitted_states[stream_key] = (current_hash, now)

    payload = {
        "trace": "ENTITY_TRUTH_TRACE",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(now)),
        "boundary": boundary,
        "camera_id": camera_id,
        "frame_index": frame_index,
        "generation": generation,
        "raw_track_id": raw_track_id,
        "display_track_id": display_track_id,
        "semantic_track_id": semantic_track_id,
        "event_type": event_type,
        "track_object_type": track_object_type,
        "validated_presence": validated_presence,
        "visit_id": visit_id,
        "visit_role": visit_role,
        "person_state": person_state,
        "customer_analytics_eligible": customer_analytics_eligible,
        "ui_presented": ui_presented,
        "source_camera_id": source_camera_id,
        "snapshot_camera_id": snapshot_camera_id,
        "viewmodel_target_camera_id": viewmodel_target_camera_id,
        "state_live_count": state_live_count,
        "health_online_camera_count": health_online_camera_count,
        "rendered_live_count": rendered_live_count,
        "total_camera_count": total_camera_count
    }
    
    try:
        json_payload = json.dumps(payload)
        _logger.info(json_payload)
        with open(_log_file, "a", encoding="utf-8") as f:
            f.write(json_payload + "\n")
    except Exception:
        pass
