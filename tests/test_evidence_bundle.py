"""Tests for EvidenceBundle and EvidenceSelector."""

import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
import pytest
import numpy as np
import cv2

from src.evidence.persistent import PersistentEvidenceStore
from src.evidence.bundle import EvidenceBundleStore, EvidenceSelector, EvidenceBundle

@pytest.fixture
def temp_evidence_root(tmp_path):
    root = tmp_path / "runtime_evidence"
    yield root
    if root.exists():
        shutil.rmtree(root)

@pytest.fixture
def bundle_store(temp_evidence_root):
    store = PersistentEvidenceStore(root=str(temp_evidence_root), max_per_camera=5)
    return EvidenceBundleStore(store)

def test_evidence_bundle_creation_and_integrity(bundle_store, temp_evidence_root):
    # Dummy frames
    key_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    pre_frame = np.ones((480, 640, 3), dtype=np.uint8) * 10
    post_frame = np.ones((480, 640, 3), dtype=np.uint8) * 20
    roi_crop = np.ones((100, 100, 3), dtype=np.uint8) * 50
    
    observed_at = datetime.now(timezone.utc).isoformat()
    
    bundle = bundle_store.persist_bundle(
        camera_id="cam_01",
        observed_at=observed_at,
        key_frame=key_frame,
        pre_frame=pre_frame,
        post_frame=post_frame,
        roi_crop=roi_crop,
        entity_id="ENT-123",
        situation_id="SIT-456",
        detector_runtime="openvino",
        model_id="yolo11n",
        generation_id="gen-0",
        confidence=0.95,
        provenance="system",
        freshness=0.1
    )
    
    assert bundle is not None
    assert bundle.bundle_id.startswith("EVD-")
    assert bundle.source_camera == "cam_01"
    
    # Check persistence and hash integrity
    bundle_dir = temp_evidence_root / "cam_01" / bundle.bundle_id
    assert bundle_dir.exists()
    
    with open(bundle_dir / "metadata.json", "r") as f:
        meta = json.load(f)
        
    assert meta["bundle_id"] == bundle.bundle_id
    assert meta["source_camera"] == "cam_01"
    assert meta["detector_runtime"] == "openvino"
    assert meta["entity_id"] == "ENT-123"
    
    # Hash integrity
    with open(bundle_dir / "key_frame.jpg", "rb") as f:
        import hashlib
        kf_hash = hashlib.sha256(f.read()).hexdigest()
        assert kf_hash == meta["hashes"]["key_frame.jpg"]
        
def test_evidence_selector_minimal_relevant(bundle_store):
    selector = EvidenceSelector(bundle_store)
    
    # Create a buffer of 10 frames
    now = datetime.now(timezone.utc).timestamp()
    buffer = []
    for i in range(10):
        frame = np.ones((480, 640, 3), dtype=np.uint8) * i
        buffer.append((now + i, frame))
        
    # Target is frame 5
    target_ts = now + 5.1
    
    # Bbox for ROI (x1, y1, x2, y2)
    bbox = (10, 10, 110, 110)
    
    bundle = selector.select(
        camera_id="cam_02",
        frames_buffer=buffer,
        detections=[],
        tracks=[],
        target_timestamp=target_ts,
        target_bbox=bbox,
        entity_id="ENT-001"
    )
    
    assert bundle is not None
    assert bundle.key_frame_path is not None
    assert bundle.pre_frame_path is not None
    assert bundle.post_frame_path is not None
    assert bundle.roi_crop_path is not None
    
    assert "key_frame.jpg" in bundle.hashes
    assert "roi_crop.jpg" in bundle.hashes

def test_evidence_selector_missing_frame_handling(bundle_store):
    selector = EvidenceSelector(bundle_store)
    
    # Buffer with only 1 frame
    now = datetime.now(timezone.utc).timestamp()
    buffer = [(now, np.zeros((480, 640, 3), dtype=np.uint8))]
    
    bundle = selector.select(
        camera_id="cam_03",
        frames_buffer=buffer,
        detections=[],
        tracks=[],
        target_timestamp=now,
    )
    
    assert bundle is not None
    assert bundle.key_frame_path is not None
    # Pre and post should be None because there are no other frames
    assert bundle.pre_frame_path is None
    assert bundle.post_frame_path is None
    assert bundle.roi_crop_path is None
