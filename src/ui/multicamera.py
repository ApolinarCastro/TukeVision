"""Dynamic N-slot operator view model (OC-01: no four-camera assumption).

This adapter owns no capture, thread, pipeline, or frame history.  The
certified SourceManager/OperationalPipeline path supplies latest snapshots.

The camera set is configuration-driven: 1 -> 4 -> 16 -> N.  Layouts are
computed by :mod:`src.ui.grid_layout` and never hardcoded to CAM-001..004.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.ui.grid_layout import grid_layout


@dataclass(frozen=True)
class CameraPanelState:
    camera_id: str
    source_state: str = "OFFLINE"
    frame: Optional[Any] = None
    fps: float = 0.0
    frame_index: int = -1
    generation: int = 0
    last_updated_at: float = 0.0
    detections: int = 0
    track_id: Optional[str] = None
    track_status: str = ""
    track_bbox: Optional[Tuple[int, int, int, int]] = None
    bboxes: Tuple[tuple, ...] = ()
    event_id: str = ""
    event_type: str = ""
    event_confidence: Optional[float] = None
    inference_ref: str = ""
    temporal: str = ""
    behavior: str = ""
    risk: str = ""
    evidence: str = ""
    analytics_frame: Optional[Any] = None
    analytics_frame_index: int = -1
    resolution: str = ""


class MultiCameraViewModel:
    """Bounded latest-wins state for N operator panels (config-driven).

    The model separates the CAMERA CATALOG (every known camera, e.g. all
    stores' cameras in a multistore deployment) from the CURRENT VIEWPORT
    (the subset currently rendered).  ``update``/``mark_state`` accept any
    catalog camera, so late frames or state changes from a store that is no
    longer in view never raise ``unsupported camera``; their panel state is
    retained and re-enters the view when the store is selected again.
    """

    def __init__(
        self,
        camera_ids: Tuple[str, ...],
        catalog_ids: Optional[Tuple[str, ...]] = None,
    ) -> None:
        ids = tuple(str(camera_id) for camera_id in camera_ids)
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("camera_ids must be non-empty and unique")
        if catalog_ids is None:
            catalog_ids = ids
        catalog = tuple(str(camera_id) for camera_id in catalog_ids)
        if not catalog or len(set(catalog)) != len(catalog):
            raise ValueError("catalog_ids must be non-empty and unique")
        for camera_id in ids:
            if camera_id not in catalog:
                raise ValueError(f"viewport camera not in catalog: {camera_id}")
        self._catalog_ids = catalog
        self._viewport = ids
        self._panels: Dict[str, CameraPanelState] = {
            camera_id: CameraPanelState(camera_id) for camera_id in catalog
        }

    @property
    def camera_ids(self) -> Tuple[str, ...]:
        """Currently visible (viewport) camera set."""
        return self._viewport

    @property
    def catalog_ids(self) -> Tuple[str, ...]:
        """Full camera catalog (all known cameras, across stores)."""
        return self._catalog_ids

    def select_viewport(self, camera_ids: Tuple[str, ...]) -> None:
        """Switch the visible set without discarding catalog panel state."""
        ids = tuple(str(camera_id) for camera_id in camera_ids)
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("camera_ids must be non-empty and unique")
        for camera_id in ids:
            if camera_id not in self._catalog_ids:
                raise ValueError(f"unsupported camera: {camera_id}")
        self._viewport = ids

    @property
    def layout(self) -> Tuple[Tuple[str, ...], ...]:
        return tuple(tuple(row) for row in grid_layout(self._viewport))

    def update(self, camera_id: str, snapshot: Any) -> None:
        """Accept an existing manager snapshot; retain only the latest frame."""
        if camera_id not in self._panels:
            raise ValueError(f"unsupported camera: {camera_id}")
        current = self._panels[camera_id]
        frame_index = int(getattr(snapshot, "frame_index", current.frame_index))
        generation = int(getattr(snapshot, "generation", current.generation) or 0)
        # Advance if generation increased (reconnect), or same generation with advancing/equal sequence
        if generation < current.generation:
            return
        if generation == current.generation and frame_index < current.frame_index:
            return
        detections = getattr(snapshot, "detections", None)
        track_id = getattr(snapshot, "track_id", None)
        track_status = getattr(snapshot, "track_status", None)
        track_bbox = getattr(snapshot, "track_bbox", None)
        bboxes = getattr(snapshot, "bboxes", None)
        event_id = getattr(snapshot, "event_id", None)
        event_type = getattr(snapshot, "event_type", None)
        event_confidence = getattr(snapshot, "event_confidence", None)
        inference_ref = getattr(snapshot, "inference_ref", None)
        temporal = getattr(snapshot, "temporal", None)
        behavior = getattr(snapshot, "behavior", None)
        risk = getattr(snapshot, "risk", None)
        evidence = getattr(snapshot, "evidence", None)
        has_event_analytics = any(
            value not in (None, "")
            for value in (
                detections, track_id, track_bbox, bboxes, event_id, event_type,
                event_confidence, inference_ref, temporal, behavior, risk,
            )
        )
        self._panels[camera_id] = CameraPanelState(
            camera_id=camera_id,
            source_state=str(getattr(snapshot, "source_state", "OFFLINE") or "OFFLINE"),
            frame=getattr(snapshot, "frame", None),
            fps=float(getattr(snapshot, "fps", 0.0) or 0.0),
            frame_index=frame_index,
            generation=generation,
            last_updated_at=time.monotonic() if getattr(snapshot, "frame", None) is not None else current.last_updated_at,
            detections=(int(detections) if detections is not None else current.detections),
            track_id=(track_id if track_id not in (None, "") else current.track_id),
            track_status=(str(track_status) if track_status not in (None, "") else current.track_status),
            track_bbox=(tuple(track_bbox) if track_bbox is not None else current.track_bbox),
            bboxes=(tuple(tuple(item) for item in bboxes) if bboxes is not None else current.bboxes),
            event_id=(str(event_id) if event_id not in (None, "") else current.event_id),
            event_type=(str(event_type) if event_type not in (None, "") else current.event_type),
            event_confidence=(float(event_confidence) if event_confidence is not None else current.event_confidence),
            inference_ref=(str(inference_ref) if inference_ref not in (None, "") else current.inference_ref),
            temporal=(str(temporal) if temporal not in (None, "") else current.temporal),
            behavior=(str(behavior) if behavior not in (None, "") else current.behavior),
            risk=(str(risk) if risk not in (None, "") else current.risk),
            evidence=(str(evidence) if evidence not in (None, "") else current.evidence),
            analytics_frame=(
                getattr(snapshot, "frame", None)
                if has_event_analytics else current.analytics_frame
            ),
            analytics_frame_index=(
                frame_index if has_event_analytics else current.analytics_frame_index
            ),
            resolution=str(getattr(snapshot, "resolution", current.resolution) or current.resolution),
        )

    def mark_state(self, camera_id: str, source_state: str) -> None:
        if camera_id not in self._panels:
            raise ValueError(f"unsupported camera: {camera_id}")
        current = self._panels[camera_id]
        self._panels[camera_id] = CameraPanelState(
            camera_id=camera_id, source_state=source_state, frame=current.frame,
            fps=current.fps, frame_index=current.frame_index,
            detections=current.detections, track_id=current.track_id,
            track_status=current.track_status, track_bbox=current.track_bbox,
            bboxes=current.bboxes, event_id=current.event_id,
            event_type=current.event_type, event_confidence=current.event_confidence,
            inference_ref=current.inference_ref,
            temporal=current.temporal, behavior=current.behavior, risk=current.risk,
            evidence=current.evidence,
            analytics_frame=current.analytics_frame,
            analytics_frame_index=current.analytics_frame_index,
            resolution=current.resolution,
        )

    def panel(self, camera_id: str) -> CameraPanelState:
        return self._panels[camera_id]

    def snapshot(self) -> Dict[str, CameraPanelState]:
        """Panels for the current viewport (catalog state is preserved)."""
        return {camera_id: self._panels[camera_id] for camera_id in self._viewport}