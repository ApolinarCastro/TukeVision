"""QW-04 bridge for frames already flowing through the operational runtime.

This module never opens a source.  It connects the existing temporal clip,
persistent evidence and QW-00 contracts to one canonical pipeline result.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import replace
from pathlib import Path
from typing import Any, Deque, Dict, Optional

from src.evidence.clips import (
    EvidenceClipAdapter,
    TemporalClipCoordinator,
    TemporalFrameBuffer,
)
from src.review import BoundedReviewExporter, record_from_signal


logger = logging.getLogger("tukevision.runtime_qw04")


class RuntimeQw04Integration:
    """Bounded signal -> temporal clip -> QW-00 runtime linkage."""

    def __init__(
        self,
        coordinator: TemporalClipCoordinator,
        exporter: BoundedReviewExporter,
        review_target: str | Path,
        *,
        clips_enabled: bool = True,
        recent_signal_limit: int = 64,
    ) -> None:
        if recent_signal_limit < 1:
            raise ValueError("recent_signal_limit must be positive")
        self.coordinator = coordinator
        self._exporter = exporter
        self._review_target = Path(review_target)
        self._clips_enabled = bool(clips_enabled)
        self._pending_records: Dict[str, Any] = {}
        self._recent_signal_ids: Deque[str] = deque()
        self._recent_signal_set: set[str] = set()
        self._recent_signal_limit = int(recent_signal_limit)
        self._signals_seen = 0
        self._clips_available = 0
        self._clips_unavailable = 0
        self._closed = False

    @classmethod
    def from_config(
        cls,
        config: Dict[str, Any],
        *,
        evidence_root: str | Path,
        review_target: str | Path,
    ) -> "RuntimeQw04Integration":
        clip_config = config.get("clips")
        review_config = config.get("review_export")
        if not isinstance(clip_config, dict) or not isinstance(review_config, dict):
            raise ValueError("QW-04 runtime configuration is incomplete")

        max_duration = float(clip_config["max_clip_duration_seconds"])
        buffer = TemporalFrameBuffer(
            pre_roll_seconds=float(clip_config["pre_roll_seconds"]),
            retention_seconds=max_duration,
            max_frames_per_camera=int(clip_config["max_frames_per_camera"]),
            max_fps=float(clip_config["buffer_fps"]),
        )
        adapter = EvidenceClipAdapter(
            evidence_root,
            max_clips_per_camera=int(clip_config["max_clips_per_camera"]),
            max_clip_duration_seconds=max_duration,
            frame_rate=float(clip_config["buffer_fps"]),
            container=str(clip_config["container"]),
            codec=str(clip_config["codec"]),
        )
        coordinator = TemporalClipCoordinator(
            buffer,
            adapter,
            pre_roll_seconds=float(clip_config["pre_roll_seconds"]),
            post_roll_seconds=float(clip_config["post_roll_seconds"]),
            max_pending_per_camera=int(clip_config["max_pending_per_camera"]),
        )
        exporter = BoundedReviewExporter(
            max_records_total=int(review_config["max_records_total"]),
            max_records_per_camera=int(review_config["max_records_per_camera"]),
            max_records_per_signal_type=int(review_config["max_records_per_signal_type"]),
            max_records_per_rule=int(review_config["max_records_per_rule"]),
            max_candidates=int(review_config["max_candidates"]),
        )
        return cls(
            coordinator,
            exporter,
            review_target,
            clips_enabled=bool(clip_config.get("enabled", False)),
            recent_signal_limit=int(review_config["max_candidates"]),
        )

    def _remember_signal(self, signal_id: str) -> None:
        if signal_id in self._recent_signal_set:
            return
        if len(self._recent_signal_ids) >= self._recent_signal_limit:
            expired = self._recent_signal_ids.popleft()
            self._recent_signal_set.discard(expired)
        self._recent_signal_ids.append(signal_id)
        self._recent_signal_set.add(signal_id)

    def _export(self) -> None:
        try:
            self._exporter.export_jsonl(self._review_target)
        except OSError as exc:
            logger.error("QW04_REVIEW_EXPORT_FAILED error=%s", type(exc).__name__)

    def _publish_clip(self, metadata: Dict[str, Any]) -> None:
        signal_id = str(metadata.get("signal_id") or "")
        record = self._pending_records.pop(signal_id, None)
        if record is None:
            return

        if str(metadata.get("camera_id")) != record.camera_id:
            metadata = self.coordinator.adapter.unavailable(
                camera_id=record.camera_id,
                signal_id=signal_id,
                start_timestamp=float(metadata.get("start_timestamp") or 0.0),
                end_timestamp=float(metadata.get("end_timestamp") or 0.0),
                reason="clip_camera_mismatch",
            )
        available = metadata.get("availability") == "AVAILABLE"
        completed = replace(
            record,
            clip_evidence_ref=metadata.get("clip_evidence_ref"),
            clip_available=available,
            clip_sha256=metadata.get("sha256"),
            clip_duration_seconds=metadata.get("duration_seconds"),
        )
        self._exporter.offer(completed)
        self._remember_signal(signal_id)
        if available:
            self._clips_available += 1
        else:
            self._clips_unavailable += 1
        self._export()

    def _fallback_pending(self, camera_id: Optional[str], reason: str) -> None:
        for signal_id, record in tuple(self._pending_records.items()):
            if camera_id is not None and record.camera_id != camera_id:
                continue
            self._publish_clip(
                self.coordinator.adapter.unavailable(
                    camera_id=record.camera_id,
                    signal_id=signal_id,
                    start_timestamp=0.0,
                    end_timestamp=0.0,
                    reason=reason,
                )
            )

    def ingest(
        self,
        camera_id: str,
        timestamp: float,
        frame: Any,
        frame_index: int,
        result: Dict[str, Any],
    ) -> tuple[Dict[str, Any], ...]:
        """Consume the exact frame/result already produced by OperationalPipeline."""
        if self._closed:
            return ()
        try:
            completed = self.coordinator.append(
                camera_id, float(timestamp), frame, int(frame_index)
            )
            for metadata in completed:
                self._publish_clip(metadata)

            behavior = result.get("behavior")
            if behavior is None:
                return completed
            track = result.get("track")
            correlation = result.get("correlation")
            trajectory = getattr(correlation, "trajectory", None)
            event = result.get("event")
            observation = result.get("observation")
            created_at = (
                getattr(event, "timestamp", None)
                or getattr(observation, "timestamp", None)
                or ""
            )
            for signal in tuple(getattr(behavior, "signals", ()) or ()):
                signal_id = str(signal.signal_id)
                if (
                    signal_id in self._pending_records
                    or signal_id in self._recent_signal_set
                ):
                    continue
                self._signals_seen += 1
                record = record_from_signal(
                    signal,
                    tuple(getattr(behavior, "features", ()) or ()),
                    created_at=created_at,
                    track_id=getattr(track, "track_id", None),
                    trajectory_id=getattr(trajectory, "trajectory_id", None),
                )
                if record.camera_id != camera_id:
                    record = replace(record, camera_id=camera_id)
                if not self._clips_enabled:
                    self._pending_records[signal_id] = record
                    self._publish_clip(
                        self.coordinator.adapter.unavailable(
                            camera_id=camera_id,
                            signal_id=signal_id,
                            start_timestamp=timestamp,
                            end_timestamp=timestamp,
                            reason="clip_disabled",
                        )
                    )
                elif self.coordinator.request(camera_id, signal_id, timestamp):
                    self._pending_records[signal_id] = record
                else:
                    self._remember_signal(signal_id)
                    logger.info(
                        "QW04_SIGNAL_SKIPPED_PENDING_BOUND camera_id=%s",
                        camera_id,
                    )
            return completed
        except Exception as exc:
            logger.error(
                "QW04_RUNTIME_FALLBACK camera_id=%s error=%s",
                camera_id,
                type(exc).__name__,
            )
            self._fallback_pending(camera_id, "runtime_clip_integration_error")
            return ()

    def summary(self) -> Dict[str, Any]:
        return {
            "signals_seen": self._signals_seen,
            "clips_available": self._clips_available,
            "clips_unavailable": self._clips_unavailable,
            "pending_clips": self.coordinator.pending_count(),
            "review": self._exporter.stats(),
            "closed": self._closed,
        }

    def close(self) -> Dict[str, Any]:
        if self._closed:
            return self.summary()
        try:
            for metadata in self.coordinator.flush():
                self._publish_clip(metadata)
        except Exception as exc:
            logger.error("QW04_FLUSH_FAILED error=%s", type(exc).__name__)
            self._fallback_pending(None, "clip_flush_failed")
        self._fallback_pending(None, "clip_finalize_incomplete")
        self._export()
        self.coordinator.clear()
        self._closed = True
        return self.summary()
