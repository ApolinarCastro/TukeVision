"""StoreCatalog: config -> certified SourceManager/CameraDescriptor mapping.

This module is the single adapter between the approved multistore config
(AG-02) and the certified runtime contracts:

  - ``StoreConfig``/``RecorderConfig``/``CameraConfig`` (src.domain.models)
    -> ``CameraDescriptor`` (src.capture.source_manager)

Invariants:
  - SECRET_LEAK=0: passwords are resolved ONLY at build time from
    ``credentials_ref`` (env var / vault ref), live in the in-memory
    descriptor and never persist, log or appear in the catalog itself.
  - BACKWARD_COMPAT: the current baseline config block (``business`` +
    ``correlation.transitions`` with CAM-001..CAM-004) maps transparently
    onto a legacy ``STORE-001`` without breaking SourceManager.
  - NO_DUPLICATE_SOURCE_MANAGER: this catalog never owns capture threads;
    it only produces descriptors for an existing SourceManager.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from src.capture.source_manager import CameraDescriptor
from src.domain.errors import CatalogError, CredentialResolutionError
from src.domain.models import (
    CameraConfig,
    CameraHealthState,
    OrganizationConfig,
    PTZConfig,
    RecorderConfig,
    RecorderType,
    SourceType,
    StoreConfig,
    ZoneRole,
)


def _env_credential(ref: str) -> str:
    """Resolve a ``credentials_ref`` to a password from the environment."""
    key = (ref or "").strip()
    if not key:
        raise CredentialResolutionError("credentials_ref vacío")
    value = os.environ.get(key, "")
    if not value:
        raise CredentialResolutionError(
            f"credencial referenciada no resuelta: {key!r} "
            "(definir en variables de entorno, nunca en Git/TES/logs)"
        )
    return value


def _resolve_credentials(ref: str) -> tuple[str, str]:
    """Resolve ``(username, password)`` from a ``credentials_ref``.

    The referenced env var may hold a JSON object
    ``{"username": ..., "password": ...}`` or, for backward compatibility, a
    plain password string (username ``""``).  Secrets live only in memory.
    """
    blob = _env_credential(ref)
    if not blob:
        return "", ""
    try:
        parsed = json.loads(blob)
    except ValueError:
        return "", blob
    if isinstance(parsed, dict):
        return str(parsed.get("username") or ""), str(parsed.get("password") or "")
    return "", blob


def _without_userinfo(stream: str) -> str:
    """Strip ``userinfo@`` from an RTSP URI (SECRET_LEAK=0).

    Rejects streams that embed credentials: credentials must be resolved from
    ``credentials_ref`` (env/vault) at build time, never stored in config.
    """
    parts = urlsplit(stream)
    if "@" in parts.netloc:
        raise CatalogError(
            "el stream RTSP no puede contener credenciales embebidas "
            "(resolverlas vía credentials_ref en el entorno)"
        )
    return stream


def _parse_source_type(raw: Any, camera_id: str) -> SourceType:
    text = str(raw or "").strip().upper()
    try:
        return SourceType[text]
    except KeyError:
        raise CatalogError(
            f"source_type inválido para {camera_id}: {text!r}"
        ) from None


def _parse_role(raw: Any, camera_id: str) -> ZoneRole:
    text = str(raw or "HYBRID").strip().upper()
    try:
        return ZoneRole[text]
    except KeyError:
        raise CatalogError(
            f"role inválido para {camera_id}: {text!r}"
        ) from None


def _parse_recorder_type(raw: Any, recorder_id: str) -> RecorderType:
    text = str(raw or "DVR").strip().upper()
    try:
        return RecorderType[text]
    except KeyError:
        raise CatalogError(
            f"recorder_type inválido para {recorder_id}: {text!r}"
        ) from None


def _build_descriptor(
    camera: CameraConfig,
    *,
    username: str,
    password: str,
    max_width: int,
    process_every_n_frames: int,
    frame_stall_timeout_s: float,
    rtsp_open_timeout_ms: int,
) -> CameraDescriptor:
    """Builds one certified CameraDescriptor from a CameraConfig.

    For RTSP/IP sources the main stream URI is used for analytics and
    credentials are injected from ``credentials_ref`` (never embedded).
    Video files are represented with a file host through a transparent
    path (SourceManager remains the runtime owner of capture).
    """
    source_type = camera.source_type
    if source_type in (SourceType.RTSP_STREAM, SourceType.IP_CAMERA):
        stream = camera.stream_main or camera.stream_sub or ""
        if not stream.startswith("rtsp://"):
            raise CatalogError(
                f"cámara {camera.camera_id} requiere stream RTSP (main o sub)"
            )
        return CameraDescriptor(
            camera_id=camera.camera_id,
            host=_without_userinfo(stream),
            channel=camera.channel_number or 1,
            subtype=0 if camera.stream_main else 1,
            username=username,
            password=password,
            max_width=int(max_width),
            process_every_n_frames=int(process_every_n_frames),
            frame_stall_timeout_s=float(frame_stall_timeout_s),
            rtsp_open_timeout_ms=int(rtsp_open_timeout_ms),
        )
    if source_type == SourceType.VIDEO_FILE:
        if not camera.stream_main:
            raise CatalogError(
                f"cámara {camera.camera_id} VIDEO_FILE requiere stream_main con ruta"
            )
        return CameraDescriptor(
            camera_id=camera.camera_id,
            host=_file_host(camera.stream_main),
            channel=0,
            subtype=0,
            max_width=int(max_width),
            process_every_n_frames=int(process_every_n_frames),
            frame_stall_timeout_s=float(frame_stall_timeout_s),
            rtsp_open_timeout_ms=int(rtsp_open_timeout_ms),
        )
    raise CatalogError(
        f"source_type no convertible a descriptor RTSP: {source_type.value}"
    )


def _file_host(path: str) -> str:
    """Maps a local video path onto the SourceManager host contract.

    SourceManager requires an ``rtsp://``-like host string for validation,
    so video files are exposed as ``rtsp://file/<abs path>`` and consumed
    by a file-capable source factory at runtime.  The legacy run_interface
    FILE path remains untouched (this is only the multistore mapping).
    """
    p = Path(path).expanduser()
    abs_path = str(p.resolve()) if p.exists() else str(p.absolute())
    return f"rtsp://file/{abs_path}"


@dataclass(frozen=True)
class CatalogEntry:
    """A catalog camera mapped onto runtime configuration."""

    store: StoreConfig
    recorder: Optional[RecorderConfig]
    camera: CameraConfig
    descriptor: CameraDescriptor

    @property
    def camera_id(self) -> str:
        return self.camera.camera_id

    @property
    def store_id(self) -> str:
        return self.camera.store_id

    @property
    def evidence_namespace(self) -> str:
        return self.camera.evidence_namespace


class StoreCatalog:
    """Configuration-driven multistore camera catalog.

    Usage:

        catalog = StoreCatalog.from_dict(config)          # legacy or multistore
        for entry in catalog.entries():
            manager.register_source(entry.descriptor)
    """

    def __init__(self, organization: OrganizationConfig) -> None:
        self._organization = organization

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------
    @classmethod
    def from_organization(cls, organization: OrganizationConfig) -> "StoreCatalog":
        return cls(organization)

    @classmethod
    def from_dict(
        cls,
        config: Dict[str, Any],
        *,
        legacy_store_id: str = "STORE-001",
        legacy_evidence_root: str = "data/runtime_evidence",
    ) -> "StoreCatalog":
        """Builds a catalog from product config.

        Supports both the new ``multistore`` block (AG-02) and the legacy
        single-store baseline (``business`` + ``correlation``), mapping the
        legacy CAM-001..CAM-004 onto a store transparently.
        """
        if not isinstance(config, dict):
            raise CatalogError("config no es un dict")

        multistore = config.get("multistore")
        if isinstance(multistore, dict) and multistore.get("enabled", False):
            organization = _organization_from_config(multistore)
            return cls(organization)

        return cls(_legacy_organization(
            config, legacy_store_id=legacy_store_id,
            legacy_evidence_root=legacy_evidence_root,
        ))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def organization(self) -> OrganizationConfig:
        return self._organization

    def store_ids(self) -> List[str]:
        return [store.store_id for store in self.stores()]

    def stores(self) -> List[StoreConfig]:
        return self._organization.stores

    def store(self, store_id: str) -> StoreConfig:
        for store in self.stores():
            if store.store_id == store_id:
                return store
        raise CatalogError(f"tienda no encontrada: {store_id}")

    def active_stores(self) -> List[StoreConfig]:
        """Stores with at least one enabled camera (store lifecycle)."""
        return [
            store for store in self.stores()
            if any(camera.enabled for camera in store.all_cameras())
        ]

    def store_status(self, store_id: str) -> Dict[str, Any]:
        """Lifecycle/status summary for one store, without secrets or URLs."""
        store = self.store(store_id)
        all_cameras = store.all_cameras()
        enabled = [c for c in all_cameras if c.enabled]
        return {
            "store_id": store.store_id,
            "store_name": store.store_name,
            "organization_id": store.organization_id,
            "recorders": len(store.recorders),
            "direct_cameras": len(store.direct_cameras),
            "total_cameras": len(all_cameras),
            "enabled_cameras": len(enabled),
            "recorder_channels": sum(
                recorder.total_channels for recorder in store.recorders
            ),
            "evidence_namespace": store.evidence_namespace,
            "camera_ids": [camera.camera_id for camera in enabled],
        }

    def cameras(self) -> List[CameraConfig]:
        """All enabled cameras across stores, in stable order."""
        return [
            camera
            for store in self.stores()
            for camera in store.all_cameras()
            if camera.enabled
        ]

    def camera(self, camera_id: str) -> CameraConfig:
        for camera in self.cameras():
            if camera.camera_id == camera_id:
                return camera
        raise CatalogError(f"cámara no encontrada: {camera_id}")

    def camera_ids(self) -> List[str]:
        return [camera.camera_id for camera in self.cameras()]

    def camera_descriptors(
        self,
        *,
        max_width: int = 640,
        process_every_n_frames: int = 1,
        frame_stall_timeout_s: float = 10.0,
        rtsp_open_timeout_ms: int = 8000,
        password_resolver=None,
        credential_resolver=None,
    ) -> List[CatalogEntry]:
        """Maps the full catalog onto certified CameraDescriptors.

        ``credential_resolver`` receives the credential reference and must
        return ``(username, password)`` (preferred). ``password_resolver``
        receives the reference and returns a password only (username ``""``);
        kept for backward compatibility. Default resolution reads the
        referenced env var (JSON ``{"username":..., "password":...}`` or
        plain password). Secrets only live inside the in-memory descriptor.
        """
        if credential_resolver is not None:
            def _resolve(ref: str) -> tuple[str, str]:
                result = credential_resolver(ref)
                if not isinstance(result, (tuple, list)) or len(result) != 2:
                    raise CatalogError(
                        "credential_resolver debe devolver (username, password)"
                    )
                return str(result[0] or ""), str(result[1] or "")
        elif password_resolver is not None:
            def _resolve(ref: str) -> tuple[str, str]:
                return "", str(password_resolver(ref) or "")
        else:
            _resolve = _resolve_credentials

        entries: List[CatalogEntry] = []
        for store in self.stores():
            for recorder in store.recorders:
                ref = recorder.credentials_ref or ""
                username, password = _resolve(ref)
                for camera in recorder.cameras:
                    if not camera.enabled:
                        continue
                    descriptor = _build_descriptor(
                        camera,
                        username=username,
                        password=password,
                        max_width=max_width,
                        process_every_n_frames=process_every_n_frames,
                        frame_stall_timeout_s=frame_stall_timeout_s,
                        rtsp_open_timeout_ms=rtsp_open_timeout_ms,
                    )
                    entries.append(CatalogEntry(store, recorder, camera, descriptor))
            for camera in store.direct_cameras:
                if not camera.enabled:
                    continue
                if camera.source_type in (SourceType.VIDEO_FILE, SourceType.WEBCAM):
                    username, password = "", ""
                else:
                    username, password = _resolve(camera.credentials_ref or "")
                descriptor = _build_descriptor(
                    camera,
                    username=username,
                    password=password,
                    max_width=max_width,
                    process_every_n_frames=process_every_n_frames,
                    frame_stall_timeout_s=frame_stall_timeout_s,
                    rtsp_open_timeout_ms=rtsp_open_timeout_ms,
                )
                entries.append(CatalogEntry(store, None, camera, descriptor))
        return entries

    # ------------------------------------------------------------------
    # Evidence namespace routing (per store / per camera)
    # ------------------------------------------------------------------
    def evidence_root_for(self, store_id: str) -> str:
        """Evidence root (namespace) for a store (Block 6 multistore routing)."""
        return self.store(store_id).evidence_namespace

    def camera_evidence_namespace(self, camera_id: str) -> str:
        """Per-camera evidence namespace, derived from its store when absent."""
        camera = self.camera(camera_id)
        if camera.evidence_namespace:
            return camera.evidence_namespace
        store = self.store(camera.store_id)
        return f"{store.evidence_namespace.rstrip('/')}/{camera.camera_id}/"

    def evidence_routing(self) -> Dict[str, str]:
        """Mapping camera_id -> evidence namespace for the whole catalog.

        Powers JPEG/MP4/sidecar/review routing so evidence never crosses
        stores (``NO_CROSS_STORE_EVIDENCE_CONTAMINATION``).
        """
        return {
            camera.camera_id: self.camera_evidence_namespace(camera.camera_id)
            for camera in self.cameras()
        }

    # ------------------------------------------------------------------
    # Introspection (no secrets, no frames)
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        """Auditable catalog summary without credentials or URLs."""
        return {
            "organization_id": self._organization.organization_id,
            "organization_name": self._organization.organization_name,
            "total_stores": len(self.stores()),
            "stores": [
                {
                    "store_id": store.store_id,
                    "store_name": store.store_name,
                    "organization_id": store.organization_id,
                    "recorders": [
                        {
                            "recorder_id": recorder.recorder_id,
                            "recorder_type": recorder.recorder_type.value,
                            "recorder_name": recorder.recorder_name,
                            "host": recorder.host,
                            "port": recorder.port,
                            "vendor": recorder.vendor,
                            "total_channels": recorder.total_channels,
                            "defined_cameras": len(recorder.cameras),
                            "enabled_cameras": sum(
                                1 for cam in recorder.cameras if cam.enabled
                            ),
                        }
                        for recorder in store.recorders
                    ],
                    "direct_cameras": [
                        {
                            "camera_id": camera.camera_id,
                            "source_type": camera.source_type.value,
                            "role": camera.role.value,
                            "zone": camera.zone,
                            "channel_number": camera.channel_number,
                            "enabled": camera.enabled,
                            "ptz_supported": camera.ptz_capability.supported,
                        }
                        for camera in store.direct_cameras
                    ],
                    "evidence_namespace": store.evidence_namespace,
                    "total_cameras": len(store.all_cameras()),
                    "enabled_cameras": sum(
                        1 for camera in store.all_cameras() if camera.enabled
                    ),
                }
                for store in self.stores()
            ],
            "total_cameras": len(self.cameras()),
        }


def _organization_from_config(block: Dict[str, Any]) -> OrganizationConfig:
    organization_raw = block.get("organization")
    if not isinstance(organization_raw, dict):
        raise CatalogError("multistore.organization es obligatorio")
    stores_raw = block.get("stores")
    if not isinstance(stores_raw, list) or not stores_raw:
        raise CatalogError("multistore.stores debe ser una lista no vacía")
    stores = [_store_from_config(store_raw) for store_raw in stores_raw]
    return OrganizationConfig(
        organization_id=str(organization_raw.get("organization_id") or ""),
        organization_name=str(organization_raw.get("organization_name") or ""),
        created_at=str(organization_raw.get("created_at") or ""),
        stores=stores,
    )


def _store_from_config(store_raw: Dict[str, Any]) -> StoreConfig:
    recorders_raw = store_raw.get("recorders") or []
    direct_raw = store_raw.get("direct_cameras") or []
    recorders = [_recorder_from_config(item, store_raw) for item in recorders_raw]
    direct = [
        _camera_from_config(item, store_raw, recorder_id=None)
        for item in direct_raw
    ]
    return StoreConfig(
        store_id=str(store_raw.get("store_id") or ""),
        organization_id=str(store_raw.get("organization_id") or ""),
        store_name=str(store_raw.get("store_name") or ""),
        location_address=str(store_raw.get("location_address") or ""),
        timezone=str(store_raw.get("timezone") or ""),
        recorders=recorders,
        direct_cameras=direct,
        evidence_namespace=str(store_raw.get("evidence_namespace") or ""),
    )


def _recorder_from_config(
    recorder_raw: Dict[str, Any], store_raw: Dict[str, Any]
) -> RecorderConfig:
    recorder_id = str(recorder_raw.get("recorder_id") or "")
    cameras = [
        _camera_from_config(item, store_raw, recorder_id=recorder_id)
        for item in (recorder_raw.get("cameras") or [])
    ]
    return RecorderConfig(
        recorder_id=recorder_id,
        store_id=str(store_raw.get("store_id") or ""),
        recorder_name=str(recorder_raw.get("recorder_name") or ""),
        recorder_type=_parse_recorder_type(
            recorder_raw.get("recorder_type"), recorder_id
        ),
        host=str(recorder_raw.get("host") or ""),
        port=int(recorder_raw.get("port") or 0),
        vendor=str(recorder_raw.get("vendor") or ""),
        credentials_ref=str(recorder_raw.get("credentials_ref") or ""),
        total_channels=int(recorder_raw.get("total_channels") or 0),
        cameras=cameras,
    )


def _camera_from_config(
    camera_raw: Dict[str, Any], store_raw: Dict[str, Any], *, recorder_id: Optional[str]
) -> CameraConfig:
    camera_id = str(camera_raw.get("camera_id") or "")
    ptz_raw = camera_raw.get("ptz_capability") or {}
    health_raw = camera_raw.get("health") or {}
    return CameraConfig(
        camera_id=camera_id,
        store_id=str(store_raw.get("store_id") or ""),
        recorder_id=recorder_id,
        channel_number=(
            int(camera_raw["channel_number"])
            if camera_raw.get("channel_number") is not None else None
        ),
        camera_name=str(camera_raw.get("camera_name") or ""),
        source_type=_parse_source_type(
            camera_raw.get("source_type") or "RTSP_STREAM",
            camera_id,
        ),
        host=str(camera_raw.get("host") or ""),
        stream_main=str(camera_raw.get("stream_main") or ""),
        stream_sub=str(camera_raw.get("stream_sub") or ""),
        zone=str(camera_raw.get("zone") or ""),
        role=_parse_role(camera_raw.get("role"), camera_id),
        enabled=bool(camera_raw.get("enabled", True)),
        credentials_ref=str(camera_raw.get("credentials_ref") or ""),
        ptz_capability=PTZConfig(
            supported=bool(ptz_raw.get("supported", False)),
            protocol=str(ptz_raw.get("protocol") or "NONE"),
            pan_limits=tuple(ptz_raw.get("pan_limits") or (-180.0, 180.0)),
            tilt_limits=tuple(ptz_raw.get("tilt_limits") or (-90.0, 90.0)),
            zoom_supported=bool(ptz_raw.get("zoom_supported", False)),
        ),
        health=CameraHealthState(
            status=str(health_raw.get("status") or "OFFLINE"),
            current_fps=float(health_raw.get("current_fps") or 0.0),
            dropped_frames=int(health_raw.get("dropped_frames") or 0),
            connection_latency_ms=float(health_raw.get("connection_latency_ms") or 0.0),
            last_frame_timestamp=str(health_raw.get("last_frame_timestamp") or ""),
        ),
        evidence_namespace=str(camera_raw.get("evidence_namespace") or ""),
    )


def _legacy_organization(
    config: Dict[str, Any],
    *,
    legacy_store_id: str,
    legacy_evidence_root: str,
) -> OrganizationConfig:
    """Maps the certified 4-camera baseline onto a legacy STORE-001.

    Backward compatibility per AG-02 §3.2: the current baseline
    (``cams/cam_1.mp4``..``cams/cam_4.mp4`` in STORE-001) maps without
    breaking SourceManager or the existing contracts.
    """
    business = config.get("business") or {}
    store_id = str(business.get("store_id") or legacy_store_id)
    zone_cfg = config.get("zone") or {}
    correlation = config.get("correlation") or {}
    transitions = correlation.get("transitions") or []

    # Deterministic set of camera ids from transitions; fallback to legacy 4.
    camera_ids: List[str] = []
    for transition in transitions:
        for key in ("source_camera", "target_camera"):
            cam = str(transition.get(key) or "")
            if cam and cam not in camera_ids:
                camera_ids.append(cam)
    if not camera_ids:
        camera_ids = ["CAM-001", "CAM-002", "CAM-003", "CAM-004"]

    cameras: List[CameraConfig] = []
    for index, camera_id in enumerate(camera_ids, start=1):
        evidence_ns = f"{legacy_evidence_root}/{store_id}/{camera_id}/"
        cameras.append(CameraConfig(
            camera_id=camera_id,
            store_id=store_id,
            recorder_id=None,
            channel_number=index,
            camera_name=f"Cámara {index:02d}",
            source_type=SourceType.VIDEO_FILE,
            host="",
            stream_main=f"cams/cam_{index}.mp4",
            stream_sub=f"cams/cam_{index}.mp4",
            zone=str(zone_cfg.get("name") or ""),
            role="HYBRID",
            enabled=True,
            evidence_namespace=evidence_ns,
        ))

    store = StoreConfig(
        store_id=store_id,
        organization_id="org_legacy",
        store_name=f"Tienda {store_id}",
        location_address="",
        timezone="UTC",
        recorders=[],
        direct_cameras=cameras,
        evidence_namespace=f"{legacy_evidence_root}/{store_id}/",
    )
    return OrganizationConfig(
        organization_id="org_legacy",
        organization_name="TukeVision Legacy",
        created_at="2026-01-01T00:00:00Z",
        stores=[store],
    )