"""Evidence Bundle implementation for operational intelligence.

Transforms atomic evidence into compact, traceable, and reusable packages.
"""

import hashlib
import json
import logging
import os
import re
import threading
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Optional, List, Tuple

import cv2
import numpy as np

from src.evidence.persistent import PersistentEvidenceStore, PersistentEvidenceError

logger = logging.getLogger("tukevision.evidence.bundle")


@dataclass
class EvidenceBundle:
    """A compact, traceable package of evidence for a specific observation or event."""
    bundle_id: str
    source_camera: str
    observed_at: str
    created_at: str
    
    # Core frames (these will be stored as files, paths stored here)
    key_frame_path: Optional[str] = None
    pre_frame_path: Optional[str] = None
    post_frame_path: Optional[str] = None
    roi_crop_path: Optional[str] = None
    
    # Metadata
    entity_id: Optional[str] = None
    situation_id: Optional[str] = None
    
    # Provenance
    detector_runtime: str = "unknown"
    model_id: str = "unknown"
    generation_id: str = "unknown"
    confidence: float = 0.0
    provenance: str = "system"
    freshness: float = 0.0
    
    # Security / Integrity
    hashes: Dict[str, str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.hashes is None:
            self.hashes = {}
        if self.metadata is None:
            self.metadata = {}


class EvidenceBundleStore:
    """Stores EvidenceBundle packages atomically on disk."""
    
    def __init__(self, persistent_store: Any, bundle_root: Optional[str] = None):
        import threading
        self.store = persistent_store
        self.bundle_root = Path(bundle_root) if bundle_root else None
        if self.bundle_root:
            self.bundle_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        
    def _encode_and_hash(self, frame: np.ndarray, quality: int) -> Tuple[bytes, str]:
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            raise PersistentEvidenceError("Failed to encode JPEG frame")
        payload = encoded.tobytes()
        digest = hashlib.sha256(payload).hexdigest()
        return payload, digest
        
    def persist_bundle(
        self,
        camera_id: str,
        observed_at: str,
        key_frame: np.ndarray,
        pre_frame: Optional[np.ndarray] = None,
        post_frame: Optional[np.ndarray] = None,
        roi_crop: Optional[np.ndarray] = None,
        entity_id: Optional[str] = None,
        situation_id: Optional[str] = None,
        detector_runtime: str = "unknown",
        model_id: str = "unknown",
        generation_id: str = "unknown",
        confidence: float = 0.0,
        provenance: str = "system",
        freshness: float = 0.0,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceBundle:
        """Atomically saves a bundle of frames and its metadata."""
        if key_frame is None or key_frame.size == 0:
            raise PersistentEvidenceError("key_frame is required for a bundle")
            
        import re
        import uuid
        safe_camera = re.sub(r'[^a-zA-Z0-9_]', '_', camera_id)
        bundle_id = uuid.uuid4().hex
        relative_dir = PurePosixPath(safe_camera, bundle_id)
        
        actual_store = self.store
        if hasattr(self.store, '_store'):
            actual_store = self.store._store(camera_id)
            
        if self.bundle_root:
            target_dir = self.bundle_root.joinpath(*relative_dir.parts)
        else:
            target_dir = getattr(actual_store, 'root', Path("data/evidence_bundles")).joinpath(*relative_dir.parts)
        
        bundle = EvidenceBundle(
            bundle_id=bundle_id,
            source_camera=camera_id,
            observed_at=observed_at,
            created_at=datetime.now(timezone.utc).isoformat(),
            entity_id=entity_id,
            situation_id=situation_id,
            detector_runtime=detector_runtime,
            model_id=model_id,
            generation_id=generation_id,
            confidence=confidence,
            provenance=provenance,
            freshness=freshness,
            metadata=custom_metadata or {},
        )
        
        payloads = {}
        
        # Prepare Key Frame
        quality = getattr(actual_store, 'jpeg_quality', 90)
        kf_payload, kf_hash = self._encode_and_hash(key_frame, quality)
        bundle.hashes["key_frame.jpg"] = kf_hash
        bundle.key_frame_path = (relative_dir / "key_frame.jpg").as_posix()
        payloads["key_frame.jpg"] = kf_payload
        
        # Prepare Pre Frame
        if pre_frame is not None and pre_frame.size > 0:
            pf_payload, pf_hash = self._encode_and_hash(pre_frame, quality)
            bundle.hashes["pre_frame.jpg"] = pf_hash
            bundle.pre_frame_path = (relative_dir / "pre_frame.jpg").as_posix()
            payloads["pre_frame.jpg"] = pf_payload
            
        # Prepare Post Frame
        if post_frame is not None and post_frame.size > 0:
            pof_payload, pof_hash = self._encode_and_hash(post_frame, quality)
            bundle.hashes["post_frame.jpg"] = pof_hash
            bundle.post_frame_path = (relative_dir / "post_frame.jpg").as_posix()
            payloads["post_frame.jpg"] = pof_payload
            
        # Prepare ROI Crop
        if roi_crop is not None and roi_crop.size > 0:
            roi_payload, roi_hash = self._encode_and_hash(roi_crop, quality)
            bundle.hashes["roi_crop.jpg"] = roi_hash
            bundle.roi_crop_path = (relative_dir / "roi_crop.jpg").as_posix()
            payloads["roi_crop.jpg"] = roi_payload

        # Write atomically
        metadata_path = target_dir / "metadata.json"
        
        with self._lock:
            if hasattr(actual_store, '_enforce_retention'):
                actual_store._enforce_retention(safe_camera)
                entries = actual_store._entries(safe_camera)
                if len(entries) >= getattr(actual_store, 'max_per_camera', 1000):
                    if actual_store.retention_status(safe_camera) != "RETENTION_OK" and len(entries) >= getattr(actual_store, 'max_per_camera', 1000):
                        logger.warning("Skipping bundle creation, retention blocked.")
                        return None

            target_dir.mkdir(parents=True, exist_ok=False)
            
            for filename, payload in payloads.items():
                if hasattr(actual_store, '_atomic_write'):
                    actual_store._atomic_write(target_dir / filename, payload)
                else:
                    self._atomic_write(target_dir / filename, payload)
                
            if hasattr(actual_store, '_atomic_json'):
                actual_store._atomic_json(metadata_path, asdict(bundle))
            else:
                self._atomic_json(metadata_path, asdict(bundle))
            
            if hasattr(actual_store, '_enforce_retention'):
                actual_store._enforce_retention(safe_camera)
            
        return bundle

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        import uuid
        import os
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
        import json
        payload = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        )
        cls._atomic_write(path, payload)


class EvidenceSelector:
    """Deterministic selector to extract the minimal relevant EvidenceBundle."""
    
    def __init__(self, bundle_store: EvidenceBundleStore):
        self.bundle_store = bundle_store
        
    def select(
        self,
        camera_id: str,
        frames_buffer: List[Tuple[float, np.ndarray]], # (timestamp, frame)
        detections: List[Any],
        tracks: List[Any],
        target_timestamp: float,
        target_bbox: Optional[Tuple[int, int, int, int]] = None,
        entity_id: Optional[str] = None,
        situation_id: Optional[str] = None,
        detector_runtime: str = "unknown",
        model_id: str = "unknown",
        generation_id: str = "unknown",
        confidence: float = 0.0,
    ) -> Optional[EvidenceBundle]:
        """
        Selects PRE, KEY, and POST frames based on a target timestamp,
        and extracts an ROI crop if a bounding box is provided.
        """
        if not frames_buffer:
            return None
            
        # Sort buffer by timestamp
        sorted_buffer = sorted(frames_buffer, key=lambda x: x[0])
        
        key_frame = None
        pre_frame = None
        post_frame = None
        observed_at = None
        
        # Find key frame (closest to target_timestamp)
        closest_idx = 0
        min_diff = float("inf")
        for i, (ts, frame) in enumerate(sorted_buffer):
            diff = abs(ts - target_timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
                
        observed_at = datetime.fromtimestamp(sorted_buffer[closest_idx][0], timezone.utc).isoformat()
        key_frame = sorted_buffer[closest_idx][1]
        
        # Pre frame (e.g. 1 second before or just the first available before)
        if closest_idx > 0:
            pre_frame = sorted_buffer[max(0, closest_idx - 5)][1] # Simple offset for demo
            
        # Post frame
        if closest_idx < len(sorted_buffer) - 1:
            post_frame = sorted_buffer[min(len(sorted_buffer) - 1, closest_idx + 5)][1]
            
        roi_crop = None
        if target_bbox is not None and key_frame is not None:
            x1, y1, x2, y2 = target_bbox
            # Bound checks
            h, w = key_frame.shape[:2]
            x1 = max(0, int(x1))
            y1 = max(0, int(y1))
            x2 = min(w, int(x2))
            y2 = min(h, int(y2))
            if x2 > x1 and y2 > y1:
                roi_crop = key_frame[y1:y2, x1:x2].copy()
                
        return self.bundle_store.persist_bundle(
            camera_id=camera_id,
            observed_at=observed_at,
            key_frame=key_frame,
            pre_frame=pre_frame,
            post_frame=post_frame,
            roi_crop=roi_crop,
            entity_id=entity_id,
            situation_id=situation_id,
            detector_runtime=detector_runtime,
            model_id=model_id,
            generation_id=generation_id,
            confidence=confidence,
        )
