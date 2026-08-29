"""Per-camera frame heartbeat instrumentation (MACRO-OC-02, BLOCK C).

Non-invasive: it only observes wall-clock timestamps that the runtime already
produces (frame entering the pipeline, frame completing the pipeline,
frame rendered on canvas).  It never logs per frame; callers sample it
periodically.

It distinguishes the three distinct stalls:
  CAPTURE_STALL     - no fresh frame reached the pipeline (source/decoder/network)
  INFERENCE_STALL   - frames arrive but none completes processing (inference)
  RENDER_STALL      - frames complete processing but none is drawn (UI)
"""

from __future__ import annotations

import time
from typing import Callable, Optional, Sequence

CAPTURE_STALL = "CAPTURE_STALL"
INFERENCE_STALL = "INFERENCE_STALL"
RENDER_STALL = "RENDER_STALL"
HEALTHY = "HEALTHY"
NO_FRAME = "NO_FRAME"


class FrameHeartbeat:
    """Tracks the last received / inferred / rendered timestamp per camera."""

    def __init__(
        self,
        camera_ids: Sequence[str],
        now: Optional[Callable[[], float]] = None,
    ) -> None:
        self._camera_ids = tuple(str(item) for item in camera_ids)
        self._now = now or time.time
        self._received: dict = {}
        self._inferred: dict = {}
        self._rendered: dict = {}
        self._received_index: dict = {}
        self._inferred_index: dict = {}
        self._rendered_index: dict = {}

    def mark_received(self, camera_id: str, frame_index: int) -> None:
        self._received[camera_id] = self._now()
        self._received_index[camera_id] = int(frame_index)

    def mark_inferred(self, camera_id: str, frame_index: int) -> None:
        self._inferred[camera_id] = self._now()
        self._inferred_index[camera_id] = int(frame_index)

    def mark_rendered(self, camera_id: str, frame_index: int) -> None:
        self._rendered[camera_id] = self._now()
        self._rendered_index[camera_id] = int(frame_index)

    def per_camera(self, camera_id: str, stall_threshold_s: float = 5.0) -> dict:
        now = self._now()
        received = self._received.get(camera_id)
        inferred = self._inferred.get(camera_id)
        rendered = self._rendered.get(camera_id)
        if received is None:
            state = NO_FRAME
            age_s = None
            detail = "never received"
        elif now - received > stall_threshold_s:
            state = CAPTURE_STALL
            age_s = round(now - received, 3)
            detail = "no fresh frame reached the pipeline"
        elif inferred is None or now - inferred > stall_threshold_s:
            state = INFERENCE_STALL
            age_s = round(now - inferred, 3) if inferred is not None else None
            detail = "frames received but none completed processing"
        elif rendered is None or now - rendered > stall_threshold_s:
            state = RENDER_STALL
            age_s = round(now - rendered, 3) if rendered is not None else None
            detail = "frames processed but none rendered"
        else:
            state = HEALTHY
            age_s = 0.0
            detail = ""
        return {
            "camera_id": camera_id,
            "state": state,
            "last_received_frame_at": received,
            "last_inference_frame_at": inferred,
            "last_rendered_frame_at": rendered,
            "age_s": age_s,
            "detail": detail,
        }

    def snapshot(self, stall_threshold_s: float = 5.0) -> dict:
        return {
            camera_id: self.per_camera(camera_id, stall_threshold_s)
            for camera_id in self._camera_ids
        }

    def summary(self, stall_threshold_s: float = 5.0) -> dict:
        items = self.snapshot(stall_threshold_s)
        counts: dict = {}
        for item in items.values():
            counts[item["state"]] = counts.get(item["state"], 0) + 1
        return {"per_camera": items, "counts": counts}


__all__ = [
    "CAPTURE_STALL",
    "INFERENCE_STALL",
    "RENDER_STALL",
    "HEALTHY",
    "NO_FRAME",
    "FrameHeartbeat",
]