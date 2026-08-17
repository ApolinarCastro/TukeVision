"""Minimal four-slot operator view model.

This adapter owns no capture, thread, pipeline, or frame history.  The
certified SourceManager/OperationalPipeline path supplies latest snapshots.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


CAMERA_IDS: Tuple[str, ...] = ("CAM-001", "CAM-002", "CAM-003", "CAM-004")
PANEL_LAYOUT: Tuple[Tuple[str, str], Tuple[str, str]] = (
    ("CAM-001", "CAM-002"),
    ("CAM-003", "CAM-004"),
)


@dataclass(frozen=True)
class CameraPanelState:
    camera_id: str
    source_state: str = "OFFLINE"
    frame: Optional[Any] = None
    fps: float = 0.0
    frame_index: int = -1


class MultiCameraViewModel:
    """Bounded latest-wins state for exactly four operator panels."""

    def __init__(self, camera_ids: Tuple[str, ...] = CAMERA_IDS) -> None:
        if tuple(camera_ids) != CAMERA_IDS:
            raise ValueError("multicamera view requires CAM-001..CAM-004")
        self._panels: Dict[str, CameraPanelState] = {
            camera_id: CameraPanelState(camera_id) for camera_id in CAMERA_IDS
        }

    @property
    def layout(self) -> Tuple[Tuple[str, str], Tuple[str, str]]:
        return PANEL_LAYOUT

    def update(self, camera_id: str, snapshot: Any) -> None:
        """Accept an existing manager snapshot; retain only the latest frame."""
        if camera_id not in self._panels:
            raise ValueError(f"unsupported camera: {camera_id}")
        current = self._panels[camera_id]
        frame_index = int(getattr(snapshot, "frame_index", current.frame_index))
        if frame_index < current.frame_index:
            return
        self._panels[camera_id] = CameraPanelState(
            camera_id=camera_id,
            source_state=str(getattr(snapshot, "source_state", "OFFLINE") or "OFFLINE"),
            frame=getattr(snapshot, "frame", None),
            fps=float(getattr(snapshot, "fps", 0.0) or 0.0),
            frame_index=frame_index,
        )

    def mark_state(self, camera_id: str, source_state: str) -> None:
        if camera_id not in self._panels:
            raise ValueError(f"unsupported camera: {camera_id}")
        current = self._panels[camera_id]
        self._panels[camera_id] = CameraPanelState(
            camera_id=camera_id, source_state=source_state, frame=current.frame,
            fps=current.fps, frame_index=current.frame_index,
        )

    def panel(self, camera_id: str) -> CameraPanelState:
        return self._panels[camera_id]

    def snapshot(self) -> Dict[str, CameraPanelState]:
        return dict(self._panels)
