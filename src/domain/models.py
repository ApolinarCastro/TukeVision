"""Entity models for the multistore domain (AG-02 contract).

Implements the approved hierarchical model:

    ORGANIZATION -> STORE -> RECORDER -> CAMERA

Credential policy (SECRET_LEAK=0): the models carry only a
``credentials_ref`` string that points to a secure vault key / env var.
Plaintext secrets are never stored on these objects nor persisted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from src.domain.errors import DomainValidationError

SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")
CAMERA_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")
EVIDENCE_NAMESPACE_RE = re.compile(r"^[A-Za-z0-9_./-]+$")
HOST_RE = re.compile(
    r"^([0-9]{1,3}\.){3}[0-9]{1,3}$|^[A-Za-z0-9_.-]+$"
)


class SourceType(Enum):
    """Source type per AG-02 §2.4 (``source_type``)."""

    RTSP_STREAM = "RTSP_STREAM"
    VIDEO_FILE = "VIDEO_FILE"
    IP_CAMERA = "IP_CAMERA"
    WEBCAM = "WEBCAM"


class ZoneRole(Enum):
    """Camera role per AG-02 §2.4 (``role``)."""

    MONITORING = "MONITORING"
    ANALYTICS = "ANALYTICS"
    HYBRID = "HYBRID"


class RecorderType(Enum):
    """Recorder kind per AG-02 §2.3 (``recorder_type``)."""

    DVR = "DVR"
    NVR = "NVR"
    VMS_BRIDGE = "VMS_BRIDGE"
    VIRTUAL_MATRIX = "VIRTUAL_MATRIX"


def _require_slug(value: str, field_name: str) -> str:
    text = (value or "").strip()
    if not text:
        raise DomainValidationError(f"{field_name} es obligatorio")
    if not SLUG_RE.match(text):
        raise DomainValidationError(
            f"{field_name} solo admite letras, números, guiones y guion bajo: {text!r}"
        )
    return text


def _require_host(value: str, field_name: str) -> str:
    text = (value or "").strip()
    if not text:
        raise DomainValidationError(f"{field_name} es obligatorio")
    if not HOST_RE.match(text):
        raise DomainValidationError(f"{field_name} no es un host/ip válido: {text!r}")
    return text


@dataclass(frozen=True)
class PTZConfig:
    """PTZ capability per AG-02 §2.5."""

    supported: bool = False
    protocol: str = "NONE"
    pan_limits: Tuple[float, float] = (-180.0, 180.0)
    tilt_limits: Tuple[float, float] = (-90.0, 90.0)
    zoom_supported: bool = False


@dataclass(frozen=True)
class CameraHealthState:
    """Runtime health snapshot per AG-02 §2.5."""

    status: str = "OFFLINE"  # ONLINE | DEGRADED | OFFLINE
    current_fps: float = 0.0
    dropped_frames: int = 0
    connection_latency_ms: float = 0.0
    last_frame_timestamp: str = ""


@dataclass(frozen=True)
class CameraConfig:
    """Camera entity per AG-02 §2.4."""

    camera_id: str
    store_id: str
    recorder_id: Optional[str]
    channel_number: Optional[int]
    camera_name: str
    source_type: SourceType
    host: str
    stream_main: str
    stream_sub: str
    zone: str = ""
    role: ZoneRole = ZoneRole.HYBRID
    enabled: bool = True
    credentials_ref: str = ""
    ptz_capability: PTZConfig = field(default_factory=PTZConfig)
    health: CameraHealthState = field(default_factory=CameraHealthState)
    evidence_namespace: str = "data/evidence"

    def __post_init__(self) -> None:
        object.__setattr__(self, "camera_id", _require_slug(self.camera_id, "camera_id"))
        object.__setattr__(self, "store_id", _require_slug(self.store_id, "store_id"))
        if self.recorder_id is not None:
            object.__setattr__(
                self, "recorder_id", _require_slug(self.recorder_id, "recorder_id")
            )
        if self.channel_number is not None and self.channel_number < 1:
            raise DomainValidationError("channel_number debe ser >= 1")
        object.__setattr__(self, "camera_name", (self.camera_name or "").strip())
        if not self.camera_name:
            raise DomainValidationError("camera_name es obligatorio")
        if self.host:
            object.__setattr__(self, "host", _require_host(self.host, "host"))
        for stream_field in ("stream_main", "stream_sub"):
            value = getattr(self, stream_field)
            if not value:
                continue
            if self.source_type in (SourceType.RTSP_STREAM, SourceType.IP_CAMERA):
                if not value.startswith("rtsp://"):
                    raise DomainValidationError(
                        f"{stream_field} debe ser una URL rtsp:// válida "
                        f"para source_type={self.source_type.value}"
                    )
            elif self.source_type == SourceType.VIDEO_FILE:
                if value.startswith("rtsp://"):
                    raise DomainValidationError(
                        f"{stream_field} para VIDEO_FILE debe ser una ruta "
                        "local, no una URL rtsp://"
                    )
        creds = (self.credentials_ref or "").strip()
        object.__setattr__(self, "credentials_ref", creds)
        ns = (self.evidence_namespace or "").strip()
        if not ns:
            raise DomainValidationError("evidence_namespace es obligatorio")
        if not EVIDENCE_NAMESPACE_RE.match(ns):
            raise DomainValidationError(
                f"evidence_namespace inválido: {ns!r}"
            )
        object.__setattr__(self, "evidence_namespace", ns)


@dataclass(frozen=True)
class RecorderConfig:
    """Recorder entity per AG-02 §2.3."""

    recorder_id: str
    store_id: str
    recorder_name: str
    recorder_type: RecorderType
    host: str
    port: int
    vendor: str
    credentials_ref: str
    total_channels: int
    cameras: List[CameraConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "recorder_id", _require_slug(self.recorder_id, "recorder_id"))
        object.__setattr__(self, "store_id", _require_slug(self.store_id, "store_id"))
        object.__setattr__(self, "recorder_name", (self.recorder_name or "").strip())
        if not self.recorder_name:
            raise DomainValidationError("recorder_name es obligatorio")
        object.__setattr__(self, "host", _require_host(self.host, "host"))
        if self.port < 1 or self.port > 65535:
            raise DomainValidationError("port debe estar entre 1 y 65535")
        if self.total_channels < 1:
            raise DomainValidationError("total_channels debe ser >= 1")
        creds = (self.credentials_ref or "").strip()
        if not creds:
            raise DomainValidationError("credentials_ref es obligatorio")
        object.__setattr__(self, "credentials_ref", creds)
        object.__setattr__(self, "cameras", list(self.cameras))


@dataclass(frozen=True)
class StoreConfig:
    """Store entity per AG-02 §2.2."""

    store_id: str
    organization_id: str
    store_name: str
    location_address: str
    timezone: str
    recorders: List[RecorderConfig] = field(default_factory=list)
    direct_cameras: List[CameraConfig] = field(default_factory=list)
    evidence_namespace: str = "data/evidence"

    def __post_init__(self) -> None:
        object.__setattr__(self, "store_id", _require_slug(self.store_id, "store_id"))
        object.__setattr__(
            self, "organization_id", _require_slug(self.organization_id, "organization_id")
        )
        object.__setattr__(self, "store_name", (self.store_name or "").strip())
        if not self.store_name:
            raise DomainValidationError("store_name es obligatorio")
        object.__setattr__(self, "location_address", (self.location_address or "").strip())
        object.__setattr__(self, "timezone", (self.timezone or "").strip())
        if not self.timezone:
            raise DomainValidationError("timezone es obligatorio")
        object.__setattr__(self, "recorders", list(self.recorders))
        object.__setattr__(self, "direct_cameras", list(self.direct_cameras))
        ns = (self.evidence_namespace or "").strip()
        if not ns:
            raise DomainValidationError("evidence_namespace es obligatorio")
        if not EVIDENCE_NAMESPACE_RE.match(ns):
            raise DomainValidationError(f"evidence_namespace inválido: {ns!r}")
        object.__setattr__(self, "evidence_namespace", ns)

    def all_cameras(self) -> List[CameraConfig]:
        """Cámaras de grabadores + cámaras IP directas, en orden estable."""
        cameras: List[CameraConfig] = []
        for recorder in self.recorders:
            cameras.extend(recorder.cameras)
        cameras.extend(self.direct_cameras)
        return cameras


@dataclass(frozen=True)
class OrganizationConfig:
    """Organization entity per AG-02 §2.1."""

    organization_id: str
    organization_name: str
    created_at: str
    stores: List[StoreConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "organization_id", _require_slug(self.organization_id, "organization_id")
        )
        object.__setattr__(self, "organization_name", (self.organization_name or "").strip())
        if not self.organization_name:
            raise DomainValidationError("organization_name es obligatorio")
        object.__setattr__(self, "created_at", (self.created_at or "").strip())
        if not self.created_at:
            raise DomainValidationError("created_at es obligatorio")
        object.__setattr__(self, "stores", list(self.stores))

    def all_stores(self) -> List[StoreConfig]:
        return list(self.stores)