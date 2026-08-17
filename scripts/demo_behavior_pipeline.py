"""Deterministic four-camera behavior/risk demo; no camera or model required."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.behavior import BehaviorEngine
from src.correlation.contracts import CrossCameraLink, TrackReference, Trajectory
from src.temporal.contract import LocalTrack, TemporalActivity


def main() -> None:
    track = LocalTrack("LOCAL-1", "CAM-001", "person", "2026-08-17T10:00:00Z",
                       "2026-08-17T10:00:45Z", event_count=4,
                       evidence_refs={"first": "evidence/first.jpg", "latest": "evidence/latest.jpg", "best": "evidence/latest.jpg"})
    activity = TemporalActivity("ACT-1", track.track_id, track.camera_id, "PERSON_PRESENCE",
                                track.started_at, track.last_seen_at, duration_ms=45000,
                                event_count=4, evidence_refs=track.evidence_refs)
    nodes = tuple(TrackReference(f"CAM-00{i}", f"LOCAL-{i}", "person",
                                 f"2026-08-17T10:00:{i*10:02d}Z", f"2026-08-17T10:00:{i*10+5:02d}Z",
                                 (f"evidence/cam{i}.jpg",)) for i in range(1, 5))
    edges = tuple(CrossCameraLink(f"LINK-{i}", f"CAND-{i}", nodes[i].track_id,
                                  nodes[i+1].track_id, nodes[i].camera_id, nodes[i+1].camera_id,
                                  5, (("temporal", .7), ("topology", .3)), .9,
                                  nodes[i].evidence_refs) for i in range(3))
    trajectory = Trajectory("TRAJ-DEMO", nodes, edges, nodes[0].start_time, nodes[-1].end_time,
                            tuple(f"evidence/cam{i}.jpg" for i in range(1, 5)),
                            (("method", "temporal_topological"),))
    observation = SimpleNamespace(observation_id="OBS-DEMO", camera_id="CAM-001",
                                  evidence_ref="evidence/first.jpg")
    event = SimpleNamespace(event_id="EVT-DEMO", camera_id="CAM-001",
                            timestamp=track.last_seen_at,
                            evidence_ref="evidence/latest.jpg")
    result = BehaviorEngine().evaluate(observation=observation, event=event,
                                       track=track, activity=activity,
                                       trajectory=trajectory)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
