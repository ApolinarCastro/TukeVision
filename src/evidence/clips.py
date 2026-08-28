"""Bounded temporal evidence clips using the approved PyAV backend.

This module consumes frames already present in the existing camera flow. It
does not open cameras or create a second capture pipeline.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import tempfile
import threading
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, Optional

from src.review.exporter import (
    RETENTION_CAPACITY_BLOCKED_BY_PROTECTED_REVIEWS,
    RETENTION_OK,
    ReviewRetentionState,
    load_review_retention_state,
)


logger = logging.getLogger("tukevision.evidence.clip_retention")


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _component(value: str, field: str) -> str:
    value = str(value)
    if not _SAFE_COMPONENT.fullmatch(value) or value in {".", ".."}:
        raise ValueError(f"invalid {field}")
    return value


@dataclass(frozen=True)
class BufferedFrame:
    timestamp: float
    frame: Any
    frame_index: int


class TemporalFrameBuffer:
    """Per-camera, sampled frame buffer with hard time and item bounds."""

    def __init__(
        self,
        *,
        pre_roll_seconds: float = 5.0,
        retention_seconds: Optional[float] = None,
        max_frames_per_camera: int = 300,
        max_fps: Optional[float] = None,
    ) -> None:
        retention = pre_roll_seconds if retention_seconds is None else retention_seconds
        if pre_roll_seconds <= 0 or retention < pre_roll_seconds:
            raise ValueError("invalid temporal buffer window")
        if max_frames_per_camera < 2 or (max_fps is not None and max_fps <= 0):
            raise ValueError("invalid temporal buffer bounds")
        self.pre_roll_seconds = float(pre_roll_seconds)
        self.retention_seconds = float(retention)
        self.max_frames_per_camera = int(max_frames_per_camera)
        self.max_fps = None if max_fps is None else float(max_fps)
        self._frames: Dict[str, Deque[BufferedFrame]] = defaultdict(deque)
        self._last_stored: Dict[str, float] = {}

    def append(self, camera_id: str, timestamp: float, frame: Any, frame_index: int) -> bool:
        camera_id = _component(camera_id, "camera_id")
        timestamp = float(timestamp)
        if not math.isfinite(timestamp):
            raise ValueError("invalid frame timestamp")
        if frame is None:
            return False
        previous = self._last_stored.get(camera_id)
        if previous is not None and timestamp < previous:
            raise ValueError("frame timestamps must be monotonic per camera")
        if self.max_fps is not None and previous is not None:
            if timestamp - previous < (1.0 / self.max_fps):
                return False
        stable_frame = frame.copy() if hasattr(frame, "copy") else frame
        items = self._frames[camera_id]
        items.append(BufferedFrame(timestamp, stable_frame, int(frame_index)))
        self._last_stored[camera_id] = timestamp
        cutoff = timestamp - self.retention_seconds
        while len(items) > self.max_frames_per_camera or (
            items and items[0].timestamp < cutoff
        ):
            items.popleft()
        return True

    def window(self, camera_id: str, start: float, end: float) -> tuple[BufferedFrame, ...]:
        camera_id = _component(camera_id, "camera_id")
        if float(end) < float(start):
            raise ValueError("clip window end precedes start")
        return tuple(
            item for item in self._frames.get(camera_id, ())
            if float(start) <= item.timestamp <= float(end)
        )

    def latest_timestamp(self, camera_id: str) -> Optional[float]:
        items = self._frames.get(_component(camera_id, "camera_id"), ())
        return items[-1].timestamp if items else None

    def clear(self, camera_id: Optional[str] = None) -> None:
        if camera_id is None:
            self._frames.clear()
            self._last_stored.clear()
        else:
            camera_id = _component(camera_id, "camera_id")
            self._frames.pop(camera_id, None)
            self._last_stored.pop(camera_id, None)


class EvidenceClipAdapter:
    """Finalize bounded frame windows as atomic, hash-addressable MP4 evidence."""

    def __init__(
        self,
        root: str | Path = "data/runtime_evidence",
        *,
        max_clips_per_camera: int = 32,
        max_clip_duration_seconds: float = 10.0,
        frame_rate: float = 5.0,
        container: str = "mp4",
        codec: str = "mpeg4",
        review_target: str | Path | None = None,
        store_id: str = "",
        organization_id: str = "",
    ) -> None:
        if max_clips_per_camera < 1 or max_clip_duration_seconds <= 0 or frame_rate <= 0:
            raise ValueError("invalid clip bounds")
        self.root = Path(root)
        self.max_clips_per_camera = int(max_clips_per_camera)
        self.max_clip_duration_seconds = float(max_clip_duration_seconds)
        self.frame_rate = float(frame_rate)
        self.container = _component(container, "container")
        self.codec = _component(codec, "codec")
        self.review_target = None if review_target is None else Path(review_target)
        self.store_id = str(store_id)
        self.organization_id = str(organization_id)
        self._retention_status: Dict[str, str] = {}
        self._lock = threading.RLock()

    def unavailable(
        self,
        *,
        camera_id: str,
        signal_id: str,
        start_timestamp: float,
        end_timestamp: float,
        reason: str = "clip_backend_unavailable",
        clip_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "clip_id": clip_id or f"CLP-{uuid.uuid4().hex.upper()}",
            "camera_id": str(camera_id),
            "store_id": self.store_id,
            "organization_id": self.organization_id,
            "signal_id": str(signal_id),
            "start_timestamp": float(start_timestamp),
            "end_timestamp": float(end_timestamp),
            "duration_seconds": max(0.0, float(end_timestamp) - float(start_timestamp)),
            "clip_evidence_ref": None,
            "relative_ref": None,
            "sha256": None,
            "availability": "UNAVAILABLE",
            "static_evidence_fallback": True,
            "error": reason,
        }

    @staticmethod
    def _atomic_json(path: Path, value: Dict[str, Any]) -> None:
        handle, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(value, stream, sort_keys=True, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise

    def _media(self, camera_id: str) -> list[Path]:
        directory = self.root / "clips" / camera_id
        if not directory.is_dir():
            return []
        return sorted(
            directory.glob(f"*.{self.container}"),
            key=lambda item: (item.stat().st_mtime_ns, item.name),
        )

    def _media_protected(
        self, target: Path, state: ReviewRetentionState
    ) -> bool:
        reference = target.relative_to(self.root).as_posix()
        signal_id = ""
        try:
            metadata = json.loads(target.with_suffix(".json").read_text(encoding="utf-8"))
            signal_id = str(metadata.get("signal_id") or "")
        except (OSError, TypeError, ValueError):
            pass
        return state.protects_clip(reference, signal_id)

    def _set_retention_status(self, camera_id: str, status: str) -> str:
        self._retention_status[camera_id] = status
        if status != RETENTION_OK:
            logger.warning("%s camera_id=%s", status, camera_id)
        return status

    def _enforce_retention(self, camera_id: str) -> str:
        directory = self.root / "clips" / camera_id
        media = self._media(camera_id)
        state = load_review_retention_state(self.review_target)
        while len(media) > self.max_clips_per_camera:
            target = next(
                (item for item in media if not self._media_protected(item, state)),
                None,
            )
            if target is None:
                return self._set_retention_status(
                    camera_id,
                    RETENTION_CAPACITY_BLOCKED_BY_PROTECTED_REVIEWS,
                )
            target.unlink(missing_ok=True)
            target.with_suffix(".json").unlink(missing_ok=True)
            media.remove(target)
        existing = {item.with_suffix(".json") for item in media}
        if directory.is_dir():
            for metadata in directory.glob("*.json"):
                reference = metadata.with_suffix(f".{self.container}").relative_to(
                    self.root
                ).as_posix()
                if metadata not in existing and not state.protects_clip(reference):
                    metadata.unlink(missing_ok=True)
        return self._set_retention_status(camera_id, RETENTION_OK)

    def enforce_retention(self, camera_id: str) -> str:
        camera_id = _component(camera_id, "camera_id")
        with self._lock:
            return self._enforce_retention(camera_id)

    def retention_status(self, camera_id: str) -> str:
        camera_id = _component(camera_id, "camera_id")
        return self._retention_status.get(camera_id, RETENTION_OK)

    def create_clip(
        self,
        *,
        camera_id: str,
        signal_id: str,
        start_timestamp: float,
        end_timestamp: float,
        frames: Iterable[BufferedFrame],
    ) -> Dict[str, Any]:
        clip_id = f"CLP-{uuid.uuid4().hex.upper()}"
        try:
            camera_id = _component(camera_id, "camera_id")
            signal_id = _component(signal_id, "signal_id")
            end_timestamp = float(end_timestamp)
            start_timestamp = max(
                float(start_timestamp), end_timestamp - self.max_clip_duration_seconds
            )
            if not math.isfinite(start_timestamp) or not math.isfinite(end_timestamp):
                raise ValueError("invalid clip timestamp")
            if end_timestamp < start_timestamp:
                raise ValueError("clip end precedes start")
        except (TypeError, ValueError):
            return self.unavailable(
                camera_id=str(camera_id), signal_id=str(signal_id),
                start_timestamp=0.0, end_timestamp=0.0,
                reason="invalid_clip_contract", clip_id=clip_id,
            )

        bounded_frames = tuple(
            item for item in frames
            if start_timestamp <= float(item.timestamp) <= end_timestamp
            and item.frame is not None
        )
        max_frames = max(2, int(math.ceil(self.max_clip_duration_seconds * self.frame_rate)) + 1)
        bounded_frames = bounded_frames[:max_frames]
        if not bounded_frames:
            return self.unavailable(
                camera_id=camera_id, signal_id=signal_id,
                start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                reason="clip_buffer_empty", clip_id=clip_id,
            )

        with self._lock:
            self._enforce_retention(camera_id)
            media = self._media(camera_id)
            state = load_review_retention_state(self.review_target)
            if len(media) >= self.max_clips_per_camera and all(
                self._media_protected(item, state) for item in media
            ):
                self._set_retention_status(
                    camera_id,
                    RETENTION_CAPACITY_BLOCKED_BY_PROTECTED_REVIEWS,
                )
                return self.unavailable(
                    camera_id=camera_id,
                    signal_id=signal_id,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp,
                    reason=RETENTION_CAPACITY_BLOCKED_BY_PROTECTED_REVIEWS,
                    clip_id=clip_id,
                )

        relative = Path("clips") / camera_id / f"{clip_id}.{self.container}"
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(
            prefix=f".{clip_id}.", suffix=f".{self.container}.tmp", dir=target.parent
        )
        os.close(handle)
        metadata_path = target.with_suffix(".json")
        try:
            import av

            with av.open(temporary_name, mode="w", format=self.container) as output:
                first = bounded_frames[0].frame
                height, width = first.shape[:2]
                stream = output.add_stream(
                    self.codec,
                    rate=Fraction(str(self.frame_rate)).limit_denominator(1000),
                )
                stream.width = int(width)
                stream.height = int(height)
                stream.pix_fmt = "yuv420p"
                for item in bounded_frames:
                    frame = item.frame
                    if frame.shape[:2] != (height, width):
                        raise ValueError("clip frames changed resolution")
                    video_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
                    for packet in stream.encode(video_frame):
                        output.mux(packet)
                for packet in stream.encode():
                    output.mux(packet)
            digest = hashlib.sha256(Path(temporary_name).read_bytes()).hexdigest()
            os.replace(temporary_name, target)
            metadata = {
                "clip_id": clip_id,
                "camera_id": camera_id,
                "store_id": self.store_id,
                "organization_id": self.organization_id,
                "signal_id": signal_id,
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "duration_seconds": max(0.0, end_timestamp - start_timestamp),
                "clip_evidence_ref": relative.as_posix(),
                "relative_ref": relative.as_posix(),
                "sha256": digest,
                "container": self.container,
                "codec": self.codec,
                "frame_rate": self.frame_rate,
                "frame_count": len(bounded_frames),
                "availability": "AVAILABLE",
                "static_evidence_fallback": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._atomic_json(metadata_path, metadata)
            with self._lock:
                self._enforce_retention(camera_id)
            return metadata
        except Exception:
            Path(temporary_name).unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            metadata_path.unlink(missing_ok=True)
            return self.unavailable(
                camera_id=camera_id, signal_id=signal_id,
                start_timestamp=start_timestamp, end_timestamp=end_timestamp,
                reason="clip_backend_unavailable", clip_id=clip_id,
            )

    @staticmethod
    def verify(metadata: Dict[str, Any], root: str | Path) -> bool:
        reference = metadata.get("clip_evidence_ref") or metadata.get("relative_ref")
        if metadata.get("availability") != "AVAILABLE" or not reference:
            return False
        root = Path(root).resolve()
        path = (root / reference).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return (
            path.is_file()
            and hashlib.sha256(path.read_bytes()).hexdigest() == metadata.get("sha256")
        )


@dataclass(frozen=True)
class PendingClip:
    camera_id: str
    signal_id: str
    signal_timestamp: float
    start_timestamp: float
    end_timestamp: float


class TemporalClipCoordinator:
    """Wait for post-roll frames before asking the adapter to finalize a clip."""

    def __init__(
        self,
        buffer: TemporalFrameBuffer,
        adapter: EvidenceClipAdapter,
        *,
        pre_roll_seconds: float = 5.0,
        post_roll_seconds: float = 5.0,
        max_pending_per_camera: int = 8,
    ) -> None:
        if pre_roll_seconds <= 0 or post_roll_seconds <= 0 or max_pending_per_camera < 1:
            raise ValueError("invalid clip coordinator bounds")
        if pre_roll_seconds + post_roll_seconds > adapter.max_clip_duration_seconds + 1e-9:
            raise ValueError("pre/post roll exceed maximum clip duration")
        self.buffer = buffer
        self.adapter = adapter
        self.pre_roll_seconds = float(pre_roll_seconds)
        self.post_roll_seconds = float(post_roll_seconds)
        self.max_pending_per_camera = int(max_pending_per_camera)
        self._pending: Dict[str, PendingClip] = {}

    def request(self, camera_id: str, signal_id: str, signal_timestamp: float) -> bool:
        camera_id = _component(camera_id, "camera_id")
        signal_id = _component(signal_id, "signal_id")
        signal_timestamp = float(signal_timestamp)
        if signal_id in self._pending:
            return False
        per_camera = sum(item.camera_id == camera_id for item in self._pending.values())
        if per_camera >= self.max_pending_per_camera:
            return False
        self._pending[signal_id] = PendingClip(
            camera_id=camera_id,
            signal_id=signal_id,
            signal_timestamp=signal_timestamp,
            start_timestamp=signal_timestamp - self.pre_roll_seconds,
            end_timestamp=signal_timestamp + self.post_roll_seconds,
        )
        return True

    def append(
        self, camera_id: str, timestamp: float, frame: Any, frame_index: int
    ) -> tuple[Dict[str, Any], ...]:
        self.buffer.append(camera_id, timestamp, frame, frame_index)
        return self.finalize_ready(camera_id, timestamp)

    def finalize_ready(
        self, camera_id: str, timestamp: float, *, force: bool = False
    ) -> tuple[Dict[str, Any], ...]:
        camera_id = _component(camera_id, "camera_id")
        timestamp = float(timestamp)
        ready = sorted(
            (
                item for item in self._pending.values()
                if item.camera_id == camera_id and (force or timestamp >= item.end_timestamp)
            ),
            key=lambda item: (item.end_timestamp, item.signal_id),
        )
        completed = []
        for item in ready:
            actual_end = item.end_timestamp if not force else min(timestamp, item.end_timestamp)
            actual_end = max(item.signal_timestamp, actual_end)
            metadata = self.adapter.create_clip(
                camera_id=item.camera_id,
                signal_id=item.signal_id,
                start_timestamp=item.start_timestamp,
                end_timestamp=actual_end,
                frames=self.buffer.window(item.camera_id, item.start_timestamp, actual_end),
            )
            completed.append(metadata)
            self._pending.pop(item.signal_id, None)
        return tuple(completed)

    def flush(self) -> tuple[Dict[str, Any], ...]:
        completed = []
        for camera_id in sorted({item.camera_id for item in self._pending.values()}):
            timestamp = self.buffer.latest_timestamp(camera_id)
            if timestamp is None:
                timestamp = max(
                    item.signal_timestamp
                    for item in self._pending.values() if item.camera_id == camera_id
                )
            completed.extend(self.finalize_ready(camera_id, timestamp, force=True))
        return tuple(completed)

    def clear(self) -> None:
        self._pending.clear()
        self.buffer.clear()

    def pending_count(self, camera_id: Optional[str] = None) -> int:
        if camera_id is None:
            return len(self._pending)
        camera_id = _component(camera_id, "camera_id")
        return sum(item.camera_id == camera_id for item in self._pending.values())
