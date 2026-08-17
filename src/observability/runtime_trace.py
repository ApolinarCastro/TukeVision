"""Bounded, secret-free stage counters for the operator runtime boundary."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path


STAGES = (
    "FRAME_RECEIVED", "FRAME_SELECTED", "INFERENCE_EXECUTED",
    "DETECTIONS_RETURNED", "TRACKS_RETURNED", "TEMPORAL_ACTIVITY_RETURNED",
    "BEHAVIOR_SIGNALS_RETURNED", "EVIDENCE_RETURNED",
    "UI_MODEL_RECEIVED", "UI_RENDERED",
)


class BoundedRuntimeTrace:
    """Keep counters and last frame indexes only; never frames, URLs or secrets."""

    def __init__(self, camera_ids):
        self._lock = threading.RLock()
        self._data = {
            camera_id: {**{stage: 0 for stage in STAGES}, "last_frame_index": -1}
            for camera_id in camera_ids
        }

    def _camera(self, camera_id):
        if camera_id not in self._data:
            raise ValueError(f"unsupported camera: {camera_id}")
        return self._data[camera_id]

    def observe_pipeline_result(self, camera_id, frame_index, result):
        with self._lock:
            row = self._camera(camera_id)
            row["FRAME_RECEIVED"] += 1
            row["last_frame_index"] = int(frame_index)
            if result.get("observation") is not None:
                row["FRAME_SELECTED"] += 1
            event = result.get("event")
            if event is not None:
                row["INFERENCE_EXECUTED"] += 1
                row["DETECTIONS_RETURNED"] += int(
                    (getattr(event, "metadata", None) or {}).get("detections", 0) or 0
                )
            if result.get("track") is not None:
                row["TRACKS_RETURNED"] += 1
            if result.get("temporal_activity") is not None:
                row["TEMPORAL_ACTIVITY_RETURNED"] += 1
            behavior = result.get("behavior")
            if behavior is not None:
                row["BEHAVIOR_SIGNALS_RETURNED"] += len(
                    tuple(getattr(behavior, "signals", ()) or ())
                )
            if result.get("evidence") is not None:
                row["EVIDENCE_RETURNED"] += 1

    def mark_ui_model_received(self, camera_id, frame_index):
        with self._lock:
            row = self._camera(camera_id)
            row["UI_MODEL_RECEIVED"] += 1
            row["last_frame_index"] = max(row["last_frame_index"], int(frame_index))

    def mark_ui_rendered(self, camera_id, frame_index):
        with self._lock:
            row = self._camera(camera_id)
            row["UI_RENDERED"] += 1
            row["last_frame_index"] = max(row["last_frame_index"], int(frame_index))

    def snapshot(self):
        with self._lock:
            return {camera_id: dict(row) for camera_id, row in self._data.items()}

    def export(self, path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_text(json.dumps(self.snapshot(), indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temp, target)
