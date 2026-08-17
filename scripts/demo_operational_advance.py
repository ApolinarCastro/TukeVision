"""Safe local demonstration of the LOOP-0018V operational chain."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.app.operational_pipeline import OperationalPipeline
from src.app.pipeline import load_config
from src.capture.source_manager import CameraDescriptor, SourceManager


class LocalSafeSource:
    source_type = "LOCAL_DEMO"
    state = "OPEN"
    last_valid_frame_age_ms = 0
    stall_count = 0
    readable_frames = 1

    def open(self):
        return SimpleNamespace(path="local-safe-frame", fps=15.0, width=120, height=80)

    def frames(self):
        frame = np.zeros((80, 120, 3), dtype="uint8")
        frame[10:60, 30:90] = 255
        yield 0, frame

    def close(self):
        self.state = "CLOSED"


def main() -> None:
    config = load_config()
    config["inference"] = dict(config["inference"])
    config["inference"]["backend"] = "deterministic"
    manager = SourceManager(source_factory=lambda descriptor: LocalSafeSource())
    manager.register_source(CameraDescriptor(camera_id="CAM-LOCAL-DEMO", host="rtsp://local.invalid"))
    trace = {}

    def capture(camera_id, source_snapshot, result):
        observation = result["observation"]
        event = result["event"]
        track = result["track"]
        evidence = result["evidence"]
        trace.update({
            "camera_id": camera_id,
            "observation_id": observation.observation_id,
            "inference_id": event.inference_ref,
            "event_id": event.event_id,
            "track_id": track.track_id,
            "evidence_id": evidence["evidence_id"],
            "evidence_ref": evidence["relative_path"],
            "sha256": evidence["sha256"],
        })

    runtime = OperationalPipeline(config, manager)
    runtime.run(lambda: bool(trace), capture)
    if not trace:
        raise RuntimeError("la demostración no produjo una cadena completa")
    print(json.dumps(trace, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
