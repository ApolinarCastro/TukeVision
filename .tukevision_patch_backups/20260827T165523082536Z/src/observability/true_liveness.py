"""True liveness per-camera (MACRO-OC-02 BLOQUE A/B).

TRUE_LIVE = SESSION_OPEN + FRESH_ADVANCING_FRAMES.
No ONLINE basado solo en cap.isOpened() o último frame almacenado.
"""

from __future__ import annotations

import hashlib
import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional


LIVE_FRAME_THRESHOLD_S = 3.0
FREEZE_HASH_WINDOW = 5  # consecutive identical frames -> STALE
STALE_TO_RECONNECT_S = 5.0


def _frame_hash(frame) -> str:
    try:
        # downscale to 16x16 grayscale for cheap hash
        import cv2
        small = cv2.resize(frame, (16, 16), interpolation=cv2.INTER_AREA)
        if len(small.shape) == 3:
            small = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return hashlib.md5(small.tobytes()).hexdigest()[:8]
    except Exception:
        try:
            return hashlib.md5(frame.tobytes()[:4096]).hexdigest()[:8]
        except Exception:
            return str(id(frame))


@dataclass
class CameraLiveness:
    camera_id: str
    liveness_state: str  # ONLINE/STALE/RECONNECTING/OFFLINE/FAILED_RECOVERABLE/STARTING
    frame_sequence: int
    last_frame_monotonic: Optional[float]
    frame_age_s: Optional[float]
    last_frame_hash: Optional[str]
    consecutive_identical: int
    reader_heartbeat: Optional[float]
    capture_state: str
    reconnect_count: int
    reader_thread_id: Optional[int]
    last_successful_decode_at: Optional[float]
    stale: bool
    live: bool


class TrueLivenessTracker:
    """Per-camera true liveness tracker (BLOQUE A/B/C)."""

    def __init__(self, camera_ids, live_threshold_s: float = LIVE_FRAME_THRESHOLD_S):
        self._ids = tuple(camera_ids)
        self._threshold = float(live_threshold_s)
        self._lock = threading.Lock()
        self._seq: Dict[str, int] = {cid: -1 for cid in self._ids}
        self._last_monotonic: Dict[str, Optional[float]] = {cid: None for cid in self._ids}
        self._last_hash: Dict[str, Optional[str]] = {cid: None for cid in self._ids}
        self._identical: Dict[str, int] = {cid: 0 for cid in self._ids}
        self._reader_hb: Dict[str, Optional[float]] = {cid: None for cid in self._ids}
        self._capture_state: Dict[str, str] = {cid: "STARTING" for cid in self._ids}
        self._reconnect: Dict[str, int] = {cid: 0 for cid in self._ids}
        self._reader_tid: Dict[str, Optional[int]] = {cid: None for cid in self._ids}
        self._last_decode: Dict[str, Optional[float]] = {cid: None for cid in self._ids}
        self._freeze_count: Dict[str, int] = {cid: 0 for cid in self._ids}
        self._liveness_state: Dict[str, str] = {cid: "STARTING" for cid in self._ids}

    def observe_frame(self, camera_id: str, frame, frame_index: int, capture_state: str = "OPEN", reader_tid: Optional[int] = None):
        now = time.monotonic()
        h = _frame_hash(frame) if frame is not None else None
        with self._lock:
            prev_seq = self._seq.get(camera_id, -1)
            if frame_index <= prev_seq:
                # no advance -> potential freeze, but hash may still differ
                pass
            else:
                self._seq[camera_id] = int(frame_index)
            self._last_monotonic[camera_id] = now
            self._capture_state[camera_id] = capture_state
            if reader_tid is not None:
                self._reader_tid[camera_id] = reader_tid
            self._reader_hb[camera_id] = now
            self._last_decode[camera_id] = now
            # hash identical detection
            prev_hash = self._last_hash.get(camera_id)
            if h is not None and prev_hash is not None and h == prev_hash:
                self._identical[camera_id] = self._identical.get(camera_id, 0) + 1
            else:
                self._identical[camera_id] = 0
            self._last_hash[camera_id] = h

    def observe_heartbeat(self, camera_id: str, capture_state: str, reconnect_count: int = 0, reader_tid: Optional[int] = None):
        with self._lock:
            self._capture_state[camera_id] = capture_state
            self._reconnect[camera_id] = int(reconnect_count)
            if reader_tid is not None:
                self._reader_tid[camera_id] = reader_tid
            # heartbeat advances even without new frame (reader alive)
            self._reader_hb[camera_id] = time.monotonic()

    def _state_for(self, camera_id: str) -> tuple[str, bool, bool]:
        now = time.monotonic()
        last = self._last_monotonic.get(camera_id)
        capture_state = self._capture_state.get(camera_id, "STARTING")
        identical = self._identical.get(camera_id, 0)
        if last is None:
            # never received frame
            if capture_state in ("RECONNECTING", "STARTING"):
                return "RECONNECTING", False, False
            return "OFFLINE", False, False
        age = now - last
        # reader heartbeat stale -> treat as stale
        rh = self._reader_hb.get(camera_id)
        reader_stale = rh is None or (now - rh) > self._threshold * 2
        if age <= self._threshold and identical < FREEZE_HASH_WINDOW and not reader_stale:
            return "ONLINE", False, True
        if capture_state in ("RECONNECTING", "STALLED"):
            return "RECONNECTING", True, False
        if age > self._threshold:
            # session open but no fresh frame
            if capture_state in ("OPEN", "READING"):
                return "STALE", True, False
            return "OFFLINE", True, False
        if identical >= FREEZE_HASH_WINDOW:
            return "STALE", True, False
        return "OFFLINE", True, False

    def snapshot(self) -> Dict[str, CameraLiveness]:
        out: Dict[str, CameraLiveness] = {}
        now = time.monotonic()
        with self._lock:
            for cid in self._ids:
                last = self._last_monotonic.get(cid)
                age = (now - last) if last is not None else None
                state, stale, live = self._state_for(cid)
                # update stored liveness for external query
                self._liveness_state[cid] = state
                if stale:
                    self._freeze_count[cid] = self._freeze_count.get(cid, 0) + 1
                out[cid] = CameraLiveness(
                    camera_id=cid,
                    liveness_state=state,
                    frame_sequence=int(self._seq.get(cid, -1)),
                    last_frame_monotonic=last,
                    frame_age_s=round(age, 3) if age is not None else None,
                    last_frame_hash=self._last_hash.get(cid),
                    consecutive_identical=int(self._identical.get(cid, 0)),
                    reader_heartbeat=self._reader_hb.get(cid),
                    capture_state=self._capture_state.get(cid, "STARTING"),
                    reconnect_count=int(self._reconnect.get(cid, 0)),
                    reader_thread_id=self._reader_tid.get(cid),
                    last_successful_decode_at=self._last_decode.get(cid),
                    stale=stale,
                    live=live,
                )
        return out

    def live_count(self) -> int:
        return sum(1 for v in self.snapshot().values() if v.live)

    def stale_count(self) -> int:
        return sum(1 for v in self.snapshot().values() if v.liveness_state == "STALE")

    def reconnecting_count(self) -> int:
        return sum(1 for v in self.snapshot().values() if v.liveness_state == "RECONNECTING")
