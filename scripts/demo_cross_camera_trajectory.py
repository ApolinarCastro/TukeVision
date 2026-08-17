"""Controlled LOOP-0018W three-camera trajectory hypothesis demo."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.correlation.correlator import CrossCameraCorrelator
from src.temporal.contract import ENDED, LocalTrack


def local_track(camera_id, number, started_at, ended_at, evidence_ref):
    return LocalTrack(
        track_id=f"TRK-{camera_id}-{number:03d}", camera_id=camera_id,
        object_type="object", started_at=started_at, last_seen_at=ended_at,
        status=ENDED, event_count=1,
        evidence_refs={"first": evidence_ref, "latest": evidence_ref, "best": evidence_ref},
    )


def main() -> None:
    config = {"correlation": {
        "enabled": True,
        "transitions": [
            {"source_camera": "CAM-01", "target_camera": "CAM-03",
             "min_transition_seconds": 1, "max_transition_seconds": 10, "enabled": True},
            {"source_camera": "CAM-03", "target_camera": "CAM-04",
             "min_transition_seconds": 1, "max_transition_seconds": 10, "enabled": True},
        ],
        "score_weights": {"temporal": 0.7, "topology": 0.3, "direction": 0.0},
        "max_active_trajectories": 8, "max_candidates_per_camera_pair": 4,
        "candidate_ttl_seconds": 60, "trajectory_ttl_seconds": 120,
    }}
    correlator = CrossCameraCorrelator.from_config(config)
    correlator.ingest(local_track("CAM-01", 1, "2026-08-17T12:00:00Z", "2026-08-17T12:00:05Z", "CAM-01/E1/frame.jpg"))
    correlator.ingest(local_track("CAM-03", 14, "2026-08-17T12:00:08Z", "2026-08-17T12:00:10Z", "CAM-03/E2/frame.jpg"))
    result = correlator.ingest(local_track("CAM-04", 8, "2026-08-17T12:00:13Z", "2026-08-17T12:00:15Z", "CAM-04/E3/frame.jpg"))
    trajectory = result.trajectory
    if trajectory is None:
        raise RuntimeError("no se produjo trayectoria controlada")
    print(json.dumps({
        "trajectory_id": trajectory.trajectory_id,
        "status": trajectory.status,
        "camera_sequence": list(trajectory.camera_sequence),
        "track_sequence": list(trajectory.track_sequence),
        "start_time": trajectory.start_time,
        "end_time": trajectory.latest_time,
        "link_count": len(trajectory.edges),
        "correlation_components": [dict(edge.score_components) for edge in trajectory.edges],
        "evidence_refs": list(trajectory.evidence_refs),
        "interpretation": "TRAJECTORY_HYPOTHESIS_NOT_IDENTITY",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
