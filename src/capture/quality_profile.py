"""Phase 12: Video Quality Profile and Adaptive HD Quality Management.

Defines the mathematical and operational contract for HD video quality,
distinguishing source, decode, display, inference, and evidence resolutions.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class QualityState(str, Enum):
    NATIVE_HD = "NATIVE_HD"
    ADAPTIVE_HD = "ADAPTIVE_HD"
    SD_SOURCE = "SD_SOURCE"
    DEGRADED_RESOURCE = "DEGRADED_RESOURCE"
    DEGRADED_NETWORK = "DEGRADED_NETWORK"
    UNKNOWN = "UNKNOWN"


class ResolutionClassification(str, Enum):
    SOURCE_LIMIT = "SOURCE_LIMIT"
    SUBSTREAM_SELECTION = "SUBSTREAM_SELECTION"
    CONFIGURATION_LIMIT = "CONFIGURATION_LIMIT"
    DECODER_LIMIT = "DECODER_LIMIT"
    PERFORMANCE_POLICY = "PERFORMANCE_POLICY"
    UI_DOWNSCALE = "UI_DOWNSCALE"
    UNKNOWN = "UNKNOWN"


@dataclass
class VideoQualityProfile:
    """Detailed resolution and quality profile per camera channel."""
    camera_id: str
    source_profile: str = "main_and_sub"
    native_width: int = 1920
    native_height: int = 1080
    source_fps: float = 30.0
    source_bitrate: int = 4096  # kbps
    codec: str = "H.264"
    
    # Resolutions per operational mode
    grid_width: int = 352
    grid_height: int = 240
    inference_width: int = 640
    inference_height: int = 360
    focus_width: int = 1920
    focus_height: int = 1080
    evidence_width: int = 1920
    evidence_height: int = 1080
    clip_width: int = 1280
    clip_height: int = 720
    
    adaptive_enabled: bool = True
    resource_state: str = "NORMAL"
    quality_state: QualityState = QualityState.ADAPTIVE_HD
    last_change_reason: str = "INITIAL_PROFILE"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if self.focus_width > self.native_width:
            self.focus_width = self.native_width
            self.focus_height = self.native_height
        if self.evidence_width > self.native_width:
            self.evidence_width = self.native_width
            self.evidence_height = self.native_height

    def get_resolution_for_mode(self, mode: str) -> Tuple[int, int]:
        if mode == "FOCUS":
            return (self.focus_width, self.focus_height)
        elif mode == "INFERENCE":
            return (self.inference_width, self.inference_height)
        elif mode == "EVIDENCE":
            return (self.evidence_width, self.evidence_height)
        elif mode == "CLIP":
            return (self.clip_width, self.clip_height)
        else:
            return (self.grid_width, self.grid_height)


class AdaptiveVideoQualityManager:
    """Manages adaptive stream selection based on view context and resource state."""

    def __init__(self):
        self.profiles: Dict[str, VideoQualityProfile] = {}
        self.current_focus_camera: Optional[str] = None
        self.resource_state: str = "NORMAL"

    def register_camera(
        self,
        camera_id: str,
        native_width: int = 1920,
        native_height: int = 1080,
        codec: str = "H.264",
    ) -> VideoQualityProfile:
        profile = VideoQualityProfile(
            camera_id=camera_id,
            native_width=native_width,
            native_height=native_height,
            codec=codec,
            grid_width=352 if native_width >= 1280 else native_width,
            grid_height=240 if native_height >= 720 else native_height,
            focus_width=native_width,
            focus_height=native_height,
            evidence_width=native_width,
            evidence_height=native_height,
            quality_state=QualityState.ADAPTIVE_HD if native_width >= 1280 else QualityState.SD_SOURCE,
        )
        self.profiles[camera_id] = profile
        return profile

    def set_focus_camera(self, camera_id: Optional[str]) -> None:
        self.current_focus_camera = camera_id

    def update_resource_state(self, resource_state: str) -> None:
        """Adapts quality states under resource pressure."""
        self.resource_state = resource_state
        for profile in self.profiles.values():
            profile.resource_state = resource_state
            if resource_state == "CRITICAL":
                profile.quality_state = QualityState.DEGRADED_RESOURCE
                profile.focus_width = min(profile.focus_width, 640)
                profile.focus_height = min(profile.focus_height, 360)
                profile.last_change_reason = "RESOURCE_CRITICAL_DEGRADATION"
            elif resource_state == "CONSTRAINED":
                profile.quality_state = QualityState.ADAPTIVE_HD
                profile.grid_width = 352
                profile.grid_height = 240
                profile.last_change_reason = "RESOURCE_CONSTRAINED_GRID_REDUCTION"
            else:
                profile.quality_state = (
                    QualityState.ADAPTIVE_HD if profile.native_width >= 1280 else QualityState.SD_SOURCE
                )
                profile.focus_width = profile.native_width
                profile.focus_height = profile.native_height
                profile.last_change_reason = "RESOURCE_NORMAL"
