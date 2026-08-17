"""Persistent, bounded evidence for the operational advance chain.

Artifacts live below a configurable runtime root.  References exposed to
domain objects are POSIX-style paths relative to that root, never machine
absolute paths.  Only already-selected frames are accepted by this store.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Optional

import cv2


class PersistentEvidenceError(Exception):
    """Invalid configuration or evidence materialization failure."""


class PersistentEvidenceStore:
    """Atomically stores selected JPEG frames and bounded metadata."""

    def __init__(
        self,
        root: str = "data/runtime_evidence",
        max_per_camera: int = 32,
        jpeg_quality: int = 90,
        id_factory: Optional[Callable[[], str]] = None,
    ) -> None:
        self.root = Path(root)
        if not 1 <= int(max_per_camera) <= 10000:
            raise PersistentEvidenceError("max_per_camera fuera de rango")
        if not 1 <= int(jpeg_quality) <= 100:
            raise PersistentEvidenceError("jpeg_quality fuera de rango")
        self.max_per_camera = int(max_per_camera)
        self.jpeg_quality = int(jpeg_quality)
        self._id_factory = id_factory or (lambda: f"EVD-{uuid.uuid4().hex.upper()}")
        self._lock = threading.RLock()

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> Optional["PersistentEvidenceStore"]:
        block = config.get("evidence") if isinstance(config, dict) else None
        if not isinstance(block, dict) or not block.get("enabled", False):
            return None
        configured_root = Path(str(block.get("root", "data/runtime_evidence")))
        if configured_root.is_absolute():
            raise PersistentEvidenceError("evidence.root debe ser relativo")
        return cls(
            root=str(configured_root),
            max_per_camera=int(block.get("max_per_camera", 32)),
            jpeg_quality=int(block.get("jpeg_quality", 90)),
        )

    @staticmethod
    def _safe_camera(camera_id: str) -> str:
        value = re.sub(r"[^A-Za-z0-9_.-]", "_", str(camera_id).strip())
        if not value or value in {".", ".."}:
            raise PersistentEvidenceError("camera_id inválido")
        return value

    def persist_selected(
        self,
        frame: Any,
        *,
        camera_id: str,
        timestamp: str,
        producer: str,
        observation_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist one policy-selected frame and return its stable record."""
        if frame is None or getattr(frame, "size", 0) == 0:
            raise PersistentEvidenceError("frame vacío")
        safe_camera = self._safe_camera(camera_id)
        evidence_id = self._id_factory()
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", evidence_id):
            raise PersistentEvidenceError("evidence_id inválido")
        relative_path = PurePosixPath(safe_camera, evidence_id, "frame.jpg")
        target = self.root.joinpath(*relative_path.parts)
        metadata_path = target.with_name("metadata.json")

        ok, encoded = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
        )
        if not ok:
            raise PersistentEvidenceError("no se pudo codificar evidencia JPEG")
        payload = encoded.tobytes()
        digest = hashlib.sha256(payload).hexdigest()
        record = {
            "evidence_id": evidence_id,
            "camera_id": str(camera_id),
            "timestamp": str(timestamp),
            "producer": str(producer),
            "observation_ref": observation_ref,
            "inference_ref": None,
            "event_ref": None,
            "track_ref": None,
            "relative_path": relative_path.as_posix(),
            "sha256": digest,
            "media_type": "image/jpeg",
        }

        with self._lock:
            target.parent.mkdir(parents=True, exist_ok=False)
            self._atomic_write(target, payload)
            self._atomic_json(metadata_path, record)
            self._enforce_retention(safe_camera)
        return dict(record)

    def link(
        self,
        evidence_ref: str,
        *,
        inference_ref: Optional[str] = None,
        event_ref: Optional[str] = None,
        track_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Atomically enrich an existing record with downstream references."""
        target = self.resolve(evidence_ref)
        metadata_path = target.with_name("metadata.json")
        with self._lock:
            try:
                record = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise PersistentEvidenceError("metadata de evidencia inválida") from exc
            record.update(
                {
                    "inference_ref": inference_ref,
                    "event_ref": event_ref,
                    "track_ref": track_ref,
                }
            )
            self._atomic_json(metadata_path, record)
        return record

    def resolve(self, evidence_ref: str) -> Path:
        """Resolve a stable reference while preventing root escape."""
        ref = PurePosixPath(str(evidence_ref))
        if ref.is_absolute() or ".." in ref.parts:
            raise PersistentEvidenceError("evidence_ref inválido")
        return self.root.joinpath(*ref.parts)

    def verify(self, evidence_ref: str) -> bool:
        target = self.resolve(evidence_ref)
        metadata_path = target.with_name("metadata.json")
        if not target.is_file() or not metadata_path.is_file():
            return False
        record = json.loads(metadata_path.read_text(encoding="utf-8"))
        return hashlib.sha256(target.read_bytes()).hexdigest() == record.get("sha256")

    def _enforce_retention(self, safe_camera: str) -> None:
        camera_dir = self.root / safe_camera
        entries = sorted(
            (p for p in camera_dir.iterdir() if p.is_dir()),
            key=lambda p: (p.stat().st_mtime_ns, p.name),
        )
        for stale in entries[: max(0, len(entries) - self.max_per_camera)]:
            for child in stale.iterdir():
                child.unlink()
            stale.rmdir()

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        finally:
            if temp.exists():
                temp.unlink()

    @classmethod
    def _atomic_json(cls, path: Path, record: Dict[str, Any]) -> None:
        payload = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        )
        cls._atomic_write(path, payload)
