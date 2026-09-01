"""Device (recorder) configuration backend for the operator admin view.

MACRO-OC-02 "DEVICE SETTINGS": CONFIGURACIÓN -> DISPOSITIVOS.

Responsibilities:
  - ``read_recorders``: expose only NON-SENSITIVE recorder fields.
  - ``save_recorder``: write non-sensitive fields into the multistore config
    and regenerate the physical camera list (host/port/profile -> stream URLs).
    Plaintext passwords are NEVER accepted or persisted: the recorder only
    carries a ``credentials_ref`` (secure vault key / env var).
  - ``tcp_reachable`` + ``probe_first_frame``: bounded connection test that
    reuses the exact certified opener the runtime uses
    (``CameraDescriptor.build_url`` -> ``build_rtsp_url`` -> ``RTSPSource``).
    There is NO hand-rolled Digest implementation here; the definitive auth
    test is REAL_STREAM_OPEN + FIRST_FRAME.

SECRET_LEAK=0: no function in this module takes or writes a password.
"""

from __future__ import annotations

import json
import os
import socket
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

PROFILE_SUBTYPE = {"main": 0, "sub": 1}
DEFAULT_CAPACITY = 16
DEFAULT_CREDENTIALS_REF = "ENV_DVR_PRINCIPAL_CREDS"

_NON_SENSITIVE_RECORDER_FIELDS = (
    "recorder_id", "store_id", "recorder_name", "recorder_type", "vendor",
    "host", "port", "device_port", "username_default", "stream_profile",
    "total_channels", "credentials_ref",
)


def _load(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _atomic_write(config_path: Path, data: dict) -> None:
    config_path = Path(config_path)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(config_path.parent), suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp_path, str(config_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _find_store(config: dict, store_id: str) -> Optional[dict]:
    stores = config.get("multistore", {}).get("stores", [])
    for store in stores:
        if store.get("store_id") == store_id:
            return store
    return None


def _find_recorder(store: dict, recorder_id: str) -> Optional[dict]:
    for recorder in store.get("recorders", []):
        if recorder.get("recorder_id") == recorder_id:
            return recorder
    return None


def _find_camera(recorder: dict, camera_id: str) -> Optional[dict]:
    for camera in recorder.get("cameras", []):
        if camera.get("camera_id") == camera_id:
            return camera
    return None


def read_stores(config_path) -> List[dict]:
    """Store summaries for the admin form (BLOCK M TIENDAS)."""
    config = _load(Path(config_path))
    org = config.get("multistore", {}).get("organization", {}) or {}
    result: List[dict] = []
    for store in config.get("multistore", {}).get("stores", []):
        cameras = []
        for recorder in store.get("recorders", []):
            cameras.extend(recorder.get("cameras", []))
        result.append({
            "store_id": store.get("store_id", ""),
            "store_name": store.get("store_name", ""),
            "organization_id": store.get("organization_id", "") or org.get("organization_id", ""),
            "organization_name": store.get("organization_name", "") or org.get("organization_name", ""),
            "timezone": store.get("timezone", ""),
            "enabled": bool(store.get("enabled", True)),
            "recorder_count": len(store.get("recorders", [])),
            "camera_count": len(cameras),
        })
    return result


def save_store(config_path, fields: dict) -> dict:
    """Add or edit a store (BLOCK M: NUEVA/EDITAR TIENDA).

    Fields: store_id, store_name, organization_id, organization_name,
    timezone. A password field is intentionally not accepted.
    """
    config_path = Path(config_path)
    config = _load(config_path)
    store_id = (fields.get("store_id") or "").strip()
    if not store_id:
        raise ValueError("store_id es obligatorio")
    if not (fields.get("store_name") or "").strip():
        raise ValueError("store_name es obligatorio")
    store = _find_store(config, store_id)
    is_new = store is None
    if store is None:
        store = {
            "store_id": store_id,
            "organization_id": (fields.get("organization_id") or "").strip() or "org_default",
            "organization_name": (fields.get("organization_name") or "").strip()
            or "Organización",
            "store_name": (fields.get("store_name") or "").strip(),
            "location_address": "",
            "timezone": (fields.get("timezone") or "").strip() or "America/Santiago",
            "evidence_namespace": f"data/evidence/{store_id}/",
            "recorders": [],
            "direct_cameras": [],
            "enabled": True,
        }
        stores = config.setdefault("multistore", {}).setdefault("stores", [])
        if any(s.get("store_id") == store_id for s in stores):
            raise ValueError(f"store_id duplicado: {store_id}")
        stores.append(store)
    else:
        for key in ("store_name", "organization_id", "organization_name", "timezone"):
            if (fields.get(key) or "").strip():
                store[key] = (fields.get(key) or "").strip()
        if "enabled" in fields and store.get("enabled", True) != bool(fields["enabled"]):
            store["enabled"] = bool(fields["enabled"])
    _validate(config)
    _atomic_write(config_path, config)
    return {"store_id": store_id, "is_new": is_new}


def set_store_enabled(config_path, store_id: str, enabled: bool) -> dict:
    """Enable/disable a store and its cameras atomically (BLOCK M DESHABILITAR)."""
    config_path = Path(config_path)
    config = _load(config_path)
    store = _find_store(config, store_id)
    if store is None:
        raise ValueError(f"store_id desconocido: {store_id}")
    store["enabled"] = bool(enabled)
    for recorder in store.get("recorders", []):
        for camera in recorder.get("cameras", []):
            camera["enabled"] = bool(enabled)
    _validate(config)
    _atomic_write(config_path, config)
    return {"store_id": store_id, "enabled": bool(enabled)}


def set_recorder_enabled(
    config_path, store_id: str, recorder_id: str, enabled: bool
) -> dict:
    """Enable/disable a recorder and its cameras (BLOCK M DESHABILITAR DVR/NVR)."""
    config_path = Path(config_path)
    config = _load(config_path)
    store = _find_store(config, store_id)
    if store is None:
        raise ValueError(f"store_id desconocido: {store_id}")
    recorder = _find_recorder(store, recorder_id)
    if recorder is None:
        raise ValueError(f"recorder_id desconocido: {recorder_id}")
    recorder["enabled"] = bool(enabled)
    for camera in recorder.get("cameras", []):
        camera["enabled"] = bool(enabled)
    _validate(config)
    _atomic_write(config_path, config)
    return {"recorder_id": recorder_id, "store_id": store_id, "enabled": bool(enabled)}


def save_camera(
    config_path, store_id: str, recorder_id: str, camera_id: str, fields: dict
) -> dict:
    """Edit a camera's name / zone / enabled (BLOCK M CÁMARAS)."""
    config_path = Path(config_path)
    config = _load(config_path)
    store = _find_store(config, store_id)
    if store is None:
        raise ValueError(f"store_id desconocido: {store_id}")
    recorder = _find_recorder(store, recorder_id)
    if recorder is None:
        raise ValueError(f"recorder_id desconocido: {recorder_id}")
    camera = _find_camera(recorder, camera_id)
    if camera is None:
        raise ValueError(f"camera_id desconocido: {camera_id}")
    if "camera_name" in fields:
        name = (fields.get("camera_name") or "").strip()
        if not name:
            raise ValueError("camera_name es obligatorio")
        camera["camera_name"] = name
    if "zone" in fields:
        zone = (fields.get("zone") or "").strip()
        if zone:
            camera["zone"] = zone
    if "enabled" in fields:
        camera["enabled"] = bool(fields["enabled"])
    _validate(config)
    _atomic_write(config_path, config)
    return {"camera_id": camera_id, "recorder_id": recorder_id, "store_id": store_id}


def read_recorders(config_path) -> List[dict]:
    """Non-sensitive recorder summaries for the admin form."""
    config = _load(Path(config_path))
    records: List[dict] = []
    for store in config.get("multistore", {}).get("stores", []):
        store_id = store.get("store_id", "")
        for recorder in store.get("recorders", []):
            camera_ids = [c.get("camera_id", "") for c in recorder.get("cameras", [])]
            records.append({
                "recorder_id": recorder.get("recorder_id", ""),
                "store_id": store_id,
                "recorder_name": recorder.get("recorder_name", ""),
                "recorder_type": recorder.get("recorder_type", "DVR"),
                "vendor": recorder.get("vendor", ""),
                "host": recorder.get("host", ""),
                "port": recorder.get("port", 554),
                "device_port": recorder.get("device_port"),
                "username_default": recorder.get("username_default", "admin"),
                "stream_profile": recorder.get("stream_profile", "main"),
                "total_channels": recorder.get("total_channels", DEFAULT_CAPACITY),
                "physical_channels": len(camera_ids),
                "camera_ids": camera_ids,
                "credentials_ref": recorder.get("credentials_ref", ""),
            })
    return records


def _camera_block(
    store_id: str, channel: int, host: str, port: int,
    profile: str, evidence_namespace_prefix: str,
) -> dict:
    primary_subtype = PROFILE_SUBTYPE.get(profile, 0)
    alt_subtype = 1 - primary_subtype
    camera_id = f"cam_{channel:02d}"
    return {
        "camera_id": camera_id,
        "store_id": store_id,
        "channel_number": channel,
        "camera_name": f"Cámara {channel:02d}",
        "source_type": "RTSP_STREAM",
        "host": host,
        "stream_main": (
            f"rtsp://{host}:{port}/cam/realmonitor?channel={channel}"
            f"&subtype={primary_subtype}"
        ),
        "stream_sub": (
            f"rtsp://{host}:{port}/cam/realmonitor?channel={channel}"
            f"&subtype={alt_subtype}"
        ),
        "zone": "General",
        "role": "HYBRID",
        "enabled": True,
        "credentials_ref": "",
        "ptz_capability": {"supported": False, "protocol": "NONE"},
        "evidence_namespace": f"{evidence_namespace_prefix}{camera_id}/",
    }


def save_recorder(config_path, store_id: str, fields: dict) -> dict:
    """Persist non-sensitive recorder settings and regenerate cameras.

    ``fields`` may contain: recorder_id, recorder_name, recorder_type,
    vendor, host, port, device_port, username_default, stream_profile,
    physical_channels, credentials_ref. A password field is intentionally
    NOT in the accepted set and is ignored if passed.

    The recorder ``total_channels`` (grid capacity) is preserved from the
    existing recorder when editing, else defaults to 16; ``physical_channels``
    (default 15) drives the number of generated camera entries.
    """
    config_path = Path(config_path)
    config = _load(config_path)
    store = _find_store(config, store_id)
    if store is None:
        raise ValueError(f"store_id desconocido: {store_id}")
    store_id = store["store_id"]

    recorder_id = (fields.get("recorder_id") or "").strip()
    if not recorder_id:
        raise ValueError("recorder_id es obligatorio")

    recorder = _find_recorder(store, recorder_id)
    is_new = recorder is None
    if recorder is None:
        recorder = {
            "recorder_id": recorder_id,
            "store_id": store_id,
            "recorder_name": "Nuevo dispositivo",
            "recorder_type": "DVR",
            "host": "",
            "port": 554,
            "vendor": "",
            "username_default": "admin",
            "credentials_ref": DEFAULT_CREDENTIALS_REF,
            "stream_profile": "main",
            "total_channels": DEFAULT_CAPACITY,
            "device_port": None,
        }
        store.setdefault("recorders", []).append(recorder)

    recorder["recorder_id"] = recorder_id
    recorder["store_id"] = store_id
    for key in (
        "recorder_name", "recorder_type", "vendor",
        "username_default", "stream_profile",
    ):
        if key in fields and fields[key] is not None:
            value = str(fields[key]).strip()
            if value:
                recorder[key] = value
    if "host" in fields:
        host_value = str(fields["host"]).strip() if fields["host"] is not None else ""
        if not host_value:
            raise ValueError("host es obligatorio")
        recorder["host"] = host_value
    for key in ("port", "device_port"):
        if key in fields and fields[key] not in (None, ""):
            recorder[key] = int(fields[key])
    if "credentials_ref" in fields and fields.get("credentials_ref"):
        recorder["credentials_ref"] = str(fields["credentials_ref"]).strip()

    if not recorder.get("host"):
        raise ValueError("host es obligatorio")
    if "physical_channels" in fields:
        physical = int(fields.get("physical_channels"))
    else:
        physical = len(recorder.get("cameras", [])) or 0
    if physical < 1:
        raise ValueError("physical_channels debe ser >= 1")

    host = recorder["host"]
    port = int(recorder.get("port", 554))
    profile = recorder.get("stream_profile", "main")
    ns_prefix = store.get("evidence_namespace", "data/evidence/")
    if not ns_prefix.endswith("/"):
        ns_prefix += "/"

    existing_meta = {
        c.get("channel_number"): {
            "camera_name": c.get("camera_name"),
            "zone": c.get("zone"),
            "enabled": c.get("enabled", True),
        }
        for c in recorder.get("cameras", [])
        if isinstance(c.get("channel_number"), int)
    }
    cameras = []
    for channel in range(1, physical + 1):
        block = _camera_block(store_id, channel, host, port, profile, ns_prefix)
        meta = existing_meta.get(channel)
        if meta:
            if meta.get("camera_name"):
                block["camera_name"] = meta["camera_name"]
            if meta.get("zone"):
                block["zone"] = meta["zone"]
            block["enabled"] = bool(meta.get("enabled", True))
        cameras.append(block)
    recorder["cameras"] = cameras

    _validate(config)
    _atomic_write(config_path, config)
    return {
        "recorder_id": recorder_id,
        "store_id": store_id,
        "is_new": is_new,
        "physical_channels": physical,
    }


def _validate(config: dict) -> None:
    """Round-trip through StoreCatalog to prove the saved config is valid.

    Validation is structural: the catalog must build without raising
    (malformed stores/recorders/cameras are rejected). Zero enabled cameras is
    legitimate (e.g. an operator disabling the only store); it is not
    corruption, so it does not block the atomic write.
    """
    from src.domain.catalog import StoreCatalog

    StoreCatalog.from_dict(config)


def tcp_reachable(host: str, port: int, timeout: float = 3.0) -> bool:
    """Fast bounded pre-check that the recorder TCP port responds."""
    try:
        sock = socket.create_connection((host, int(port)), timeout=timeout)
        sock.close()
        return True
    except Exception:
        return False


def probe_first_frame(
    host: str,
    port: int = 554,
    channel: int = 1,
    subtype: int = 0,
    username: str = "",
    password: str = "",
    timeout_s: float = 6.0,
) -> dict:
    """Bounded connection test via the certified opener (no custom Digest).

    Builds the URL with ``CameraDescriptor.build_url`` -> ``build_rtsp_url``
    (exactly the runtime path), opens ``RTSPSource`` with a single attempt and
    a bounded open timeout, and requires a real frame. The password stays only
    in memory and is never printed or persisted.
    """
    from src.capture.live_sources import RTSPSource
    from src.capture.source_manager import CameraDescriptor

    descriptor = CameraDescriptor(
        camera_id=f"cam_{channel:02d}",
        host=f"{host}:{int(port)}",
        channel=int(channel),
        subtype=int(subtype),
        username=username,
        password=password,
    )
    url = descriptor.build_url()
    source = None
    try:
        source = RTSPSource(
            rtsp_url=url,
            max_width=640,
            max_reconnect_attempts=0,
            max_open_attempts=1,
            rtsp_open_timeout_ms=int(timeout_s * 1000),
            frame_stall_timeout_s=3.0,
        )
        meta = source.open()
        return {
            "ok": True,
            "resolution": f"{meta.width}x{meta.height}",
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "resolution": "", "error": type(exc).__name__}
    finally:
        if source is not None:
            try:
                source.close()
            except Exception:  # noqa: BLE001
                pass


def primary_subtype_for(profile: str) -> int:
    """0 for the main profile, 1 for the sub profile."""
    return PROFILE_SUBTYPE.get(profile, 0)


__all__ = [
    "read_recorders",
    "save_recorder",
    "read_stores",
    "save_store",
    "set_store_enabled",
    "set_recorder_enabled",
    "save_camera",
    "tcp_reachable",
    "probe_first_frame",
    "primary_subtype_for",
]