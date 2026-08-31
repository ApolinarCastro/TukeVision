"""Controlador de la interfaz operativa local.

Responsabilidad única: orquestar la ejecución del pipeline en un hilo de
trabajo, entregar snapshots a la vista mediante una cola con backpressure
(tamaño 1, se descarta el snapshot visual viejo) y permitir detener y
cerrar de forma segura. Nunca toca widgets de Tk.
"""

import logging
import queue
import threading
from types import SimpleNamespace
from typing import Callable, Optional

import cv2

from src.app.pipeline import Pipeline, PipelineError, load_config
from src.capture.live_sources import RTSPSource, WebcamSource
from src.capture.video_source import VideoSource
from src.capture.source_manager import CameraDescriptor, SourceManager
from src.app.operational_pipeline import OperationalPipeline
from src.observability.logging_setup import redact_rtsp_url
from src.ui.state import AppStatus, UiState, followed_track_id, redact_source_display
from src.ui.multicamera import MultiCameraViewModel

logger = logging.getLogger("tukevision.ui")


class StopRequested(BaseException):
    """Solicitud de detención emitida desde el controlador.

    Hereda de BaseException para que el pipeline (que captura Exception)
    lo propague y ejecute su limpieza sin envolverlo en PipelineError.
    """


def build_source(source_kind: str, source_input: str, config: dict):
    """Construye la fuente según la selección de la interfaz.

    max_width=0 preserva la resolución original de la fuente.
    El pipeline configura su propio max_width para procesamiento analítico.
    """
    video_cfg = config.get("video", {})
    max_width = video_cfg.get("max_width", 0)
    every_n = video_cfg.get("process_every_n_frames", 1)

    if source_kind == "FILE":
        return VideoSource(
            source_input,
            max_width=max_width,
            process_every_n_frames=every_n,
        )
    if source_kind == "WEBCAM":
        index = int(source_input) if str(source_input).strip() else 0
        return WebcamSource(
            camera_index=index,
            max_width=max_width,
            process_every_n_frames=every_n,
            backend=cv2.CAP_DSHOW,
        )
    if source_kind == "RTSP":
        url = str(source_input).strip()
        if not url:
            raise ValueError("Para RTSP ingrese una URL")
        rtsp_cfg = config.get("rtsp", {})
        return RTSPSource(
            rtsp_url=url,
            max_width=max_width,
            process_every_n_frames=every_n,
            rtsp_open_timeout_ms=int(rtsp_cfg.get("open_timeout_ms", 8000)),
            rtsp_read_timeout_ms=int(rtsp_cfg.get("read_timeout_ms", 4000)),
            frame_stall_timeout_s=float(rtsp_cfg.get("frame_stall_timeout_s", 10.0)),
        )
    raise ValueError(f"Fuente no soportada: {source_kind}")


class UiController:
    """Orquesta el pipeline en un hilo y alimenta a la vista."""

    def __init__(
        self,
        config: Optional[dict] = None,
        pipeline_factory: Optional[Callable[[], Pipeline]] = None,
        source_builder: Optional[Callable] = None,
        camera_ids: Optional[tuple] = None,
    ) -> None:
        self._config = config or load_config()
        self._pipeline_factory = pipeline_factory or (lambda: Pipeline(config=self._config))
        self._source_builder = source_builder or build_source
        self._state = UiState()
        zone = self._config.get("zone", {})
        self._state.zone_id = zone.get("id", "")
        self._state.zone_name = zone.get("name", "")
        self._state.source_kind = "FILE"

        self._visual_queue: queue.Queue = queue.Queue(maxsize=1)
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        # Presentation-only orchestration for snapshots produced upstream.
        self._presentation = MultiCameraViewModel(camera_ids or ())
        self.camera_ids = camera_ids or ()

        # Focus coordinator
        self._focus_lock = threading.Lock()
        self._focus_condition = threading.Condition(self._focus_lock)
        self._pending_focus_intent = None
        self._active_focus_intent = None
        self._stop_focus_worker = False
        self._focus_worker_thread = threading.Thread(target=self._focus_worker_loop, daemon=True)
        self._focus_worker_thread.start()
        # Camera set is config-driven (OC-01): 1 -> 4 -> 16 -> N.
        # The view model holds the FULL CAMERA CATALOG (every store's
        # cameras) as ``catalog_ids`` and a CURRENT VIEWPORT subset; store
        # switching only changes the viewport, so late frames from a store
        # that is no longer visible are accepted and retained (MACRO-OC-02-A).
        if camera_ids is None:
            catalog = self._catalog_camera_ids()
            camera_ids = tuple(catalog) if catalog else ("CAM-001",)
        camera_ids = tuple(str(camera_id) for camera_id in camera_ids) or ("CAM-001",)
        self._multicamera = MultiCameraViewModel(
            camera_ids, catalog_ids=camera_ids
        )

    def _catalog_camera_ids(self) -> list:
        """Derive the operator camera set from the multistore catalog."""
        try:
            from src.domain.catalog import StoreCatalog

            catalog = StoreCatalog.from_dict(self._config)
            return catalog.camera_ids()
        except Exception:
            return []

    @property
    def status(self) -> str:
        with self._lock:
            return self._state.status

    @property
    def camera_ids(self) -> tuple:
        """Operator camera set (config-driven, N >= 1)."""
        return self._multicamera.camera_ids

    @property
    def store_id(self) -> str:
        return str(self._config.get("business", {}).get("store_id", "") or "")

    # --- Multistore selection (OC-06) ---
    def stores(self) -> list[str]:
        """Return list of available store IDs from the catalog."""
        try:
            from src.domain.catalog import StoreCatalog
            catalog = StoreCatalog.from_dict(self._config)
            return [store.store_id for store in catalog.stores()]
        except Exception:
            return [self.store_id] if self.store_id else []

    def store_cameras(self, store_id: str, zone: str = "") -> tuple[str, ...]:
        """Return camera IDs for a given store, optionally filtered by zone."""
        try:
            from src.domain.catalog import StoreCatalog
            catalog = StoreCatalog.from_dict(self._config)
            store = catalog.store(store_id)
            cameras = [
                cam.camera_id
                for cam in store.all_cameras()
                if cam.enabled and (not zone or cam.zone == zone)
            ]
            return tuple(cameras)
        except Exception:
            return ()

    def store_zones(self, store_id: str) -> list[str]:
        """Return unique zone names for a store."""
        try:
            from src.domain.catalog import StoreCatalog
            catalog = StoreCatalog.from_dict(self._config)
            store = catalog.store(store_id)
            zones = set()
            for cam in store.all_cameras():
                if cam.enabled and cam.zone:
                    zones.add(cam.zone)
            return sorted(zones)
        except Exception:
            return []

    def select_store(self, store_id: str, zone: str = "") -> None:
        """Switch the operator viewport to a different store/zone.

        The underlying view model keeps the full camera catalog: only the
        visible subset changes, so frames already flowing from the previous
        store remain valid (never ``unsupported camera``).
        """
        camera_ids = self.store_cameras(store_id, zone)
        if not camera_ids:
            # Unknown store or empty zone: keep the current viewport instead
            # of crashing on a synthetic fallback camera (MACRO-OC-02-A).
            logger.warning("STORE_SELECT_UNKNOWN store_id=%s zone=%s", store_id, zone)
            self._store_id = store_id
            self._selected_zone = zone
            return
        self._multicamera.select_viewport(camera_ids)
        self._store_id = store_id
        self._selected_zone = zone

    @property
    def current_store(self) -> str:
        return getattr(self, "_store_id", self.store_id)

    @property
    def current_zone(self) -> str:
        return getattr(self, "_selected_zone", "")

    # --- PTZ support (OC-07) ---
    def ptz_capability(self, camera_id: str):
        """Return PTZConfig for a camera if available."""
        try:
            from src.domain.catalog import StoreCatalog
            catalog = StoreCatalog.from_dict(self._config)
            cam = catalog.camera(camera_id)
            return cam.ptz_capability
        except Exception:
            from src.domain.models import PTZConfig
            return PTZConfig()

    def ptz_status(self, camera_id: str) -> dict:
        """PTZ capability status (Block 8, MACRO-OC-01-R).

        Without a real physical PTZ implementation the capability is gated:
        the camera may *declare* PTZ support in config, but the runtime does
        not certify it (``certified=False``) and will never send commands.
        """
        cap = self.ptz_capability(camera_id)
        return {
            "camera_id": camera_id,
            "supported": bool(getattr(cap, "supported", False)),
            "certified": False,
            "status": "NOT_CERTIFIED" if not getattr(cap, "supported", False)
            else "CAPABILITY_GATED",
        }

    def ptz_command(self, camera_id: str, action: str) -> bool:
        """Send PTZ command to camera. Returns True if implemented.

        There is no physical PTZ implementation (ONVIF/vendor SDK absent),
        so this is CAPABILITY_GATED and always returns False: the UI never
        shows the operator a control that silently does nothing.
        """
        return False

    def is_running(self) -> bool:
        with self._lock:
            return self._state.status == AppStatus.RUNNING

    def ingest_camera_snapshot(self, camera_id: str, snapshot) -> None:
        """Publish one existing SourceManager/OperationalPipeline snapshot.

        This method never opens a source or runs processing; it only updates
        the bounded latest-wins presentation model consumed by the UI timer.
        """
        self._multicamera.update(camera_id, snapshot)

    def mark_camera_state(self, camera_id: str, source_state: str) -> None:
        self._multicamera.mark_state(camera_id, source_state)

    def poll_multicamera(self):
        """Return the N logical panel states for the current grid."""
        return self._multicamera.snapshot()

    def start(self, source_kind: str, source_input: str) -> None:
        """Inicia el pipeline en un hilo de trabajo."""
        # Trazado seguro de apertura RTSP (LOOP-0015-TRACE, C-04)
        SOURCE_TYPE = source_kind
        RTSP_CONTROLLER_VALUE_REDACTED = (
            redact_rtsp_url(source_input) if source_kind == "RTSP" else ""
        )
        logger.info("SOURCE_TYPE=%s", SOURCE_TYPE)
        if RTSP_CONTROLLER_VALUE_REDACTED:
            logger.info(
                "RTSP_CONTROLLER_VALUE_REDACTED=%s", RTSP_CONTROLLER_VALUE_REDACTED
            )
        if self.is_running():
            raise ValueError("La interfaz ya está en ejecución")

        with self._lock:
            self._state.source_kind = source_kind
            self._state.reset_run()
            self._state.status = AppStatus.RUNNING

        self._stop.clear()
        self._drain_visual()
        self._thread = threading.Thread(
            target=self._worker,
            args=(source_kind, source_input),
            daemon=True,
        )
        self._thread.start()

    def _worker(self, source_kind: str, source_input: str) -> None:
        try:
            if source_kind == "RTSP":
                self._run_managed_rtsp(source_input)
                return
            source = self._source_builder(source_kind, source_input, self._config)
            pipeline = self._pipeline_factory()
            summary = pipeline.process_source(source, on_frame=self._on_frame)
            with self._lock:
                self._state.final_status = summary.final_status
                self._state.source_type = summary.video_path
        except StopRequested:
            with self._lock:
                self._state.final_status = "STOPPED_BY_USER"
            logger.info("Detenido por el usuario. final_status=STOPPED_BY_USER")
        except (ValueError, PipelineError) as e:
            with self._lock:
                self._state.error = str(e)
                self._state.final_status = "ERROR"
            logger.error("Error controlado en la interfaz: %s", e)
        except Exception as e:
            with self._lock:
                self._state.error = f"{type(e).__name__}: {e}"
                self._state.final_status = "ERROR"
            logger.exception("Error no controlado en la interfaz: %s", e)
        finally:
            with self._lock:
                self._state.status = AppStatus.STOPPED

    def _run_managed_rtsp(self, source_input: str) -> None:
        """Run RTSP through SourceManager and the operational advance chain."""
        url = str(source_input).strip()
        if not url:
            raise ValueError("Para RTSP ingrese una URL")
        video_cfg = self._config.get("video", {})
        rtsp_cfg = self._config.get("rtsp", {})
        camera_id = self._config.get("business", {}).get("camera_id", "CAM-001")
        manager = SourceManager()
        manager.register_source(CameraDescriptor(
            camera_id=camera_id,
            host=url,
            max_width=int(video_cfg.get("max_width", 640)),
            process_every_n_frames=int(video_cfg.get("process_every_n_frames", 1)),
            frame_stall_timeout_s=float(rtsp_cfg.get("frame_stall_timeout_s", 10.0)),
            rtsp_open_timeout_ms=int(rtsp_cfg.get("open_timeout_ms", 8000)),
        ))
        runtime = OperationalPipeline(self._config, manager)
        summary = runtime.run(self._stop.is_set, self._on_operational_result)
        with self._lock:
            self._state.final_status = summary.final_status
            self._state.source_type = "RTSP"

    def _on_operational_result(self, camera_id, source_snapshot, result) -> None:
        """Adapt an advance-chain result to the existing presentation contract."""
        track = result.get("track")
        event = result.get("event")
        evidence = result.get("evidence")
        tracked = (track,) if track is not None else ()
        snapshot = SimpleNamespace(
            frame_index=result["frame_index"],
            frame=source_snapshot["frame"],
            source_type="RTSP",
            source_path="",
            source_state=source_snapshot.get("state", "OPEN"),
            fps=float(source_snapshot.get("fps", 0.0) or 0.0),
            tracked_objects=tracked,
            stays_seconds={getattr(track, "track_id", ""): 0.0} if track else {},
            in_zone_track_ids=(),
            risk_text="Observación técnica" if event is not None else "",
            latest_alert=None,
            latest_evidence_path=(evidence or {}).get("relative_path"),
            frames_processed=result["frame_index"] + 1,
            persons_detected=1 if event is not None else 0,
            alerts_total=0,
            evidence_total=1 if evidence is not None else 0,
            timestamp=source_snapshot.get("timestamp", __import__("time").monotonic()),
            generation=source_snapshot.get("generation", 0),
            event=event,
            evidence=evidence,
        )
        self._on_frame(snapshot)

    def _on_frame(self, snapshot) -> None:
        """Callback del pipeline, ejecutado en el hilo de trabajo."""
        if self._stop.is_set():
            raise StopRequested()

        with self._lock:
            self._apply_snapshot(snapshot)
            # Legacy single-source pipeline occupies CAM-001's presentation
            # slot; multicamera callers publish their own camera_id snapshots.
            self._multicamera.update("CAM-001", snapshot)

        # Backpressure: solo se conserva el último snapshot visual
        try:
            self._visual_queue.put_nowait(snapshot)
        except queue.Full:
            try:
                self._visual_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._visual_queue.put_nowait(snapshot)
            except queue.Full:
                pass

    def _apply_snapshot(self, snapshot) -> None:
        st = self._state
        st.source_type = snapshot.source_type
        st.source_state = snapshot.source_state
        st.fps = snapshot.fps
        st.resolution = (
            f"{snapshot.frame.shape[1]}x{snapshot.frame.shape[0]}"
        )
        st.source_path_display = redact_source_display(
            st.source_kind, snapshot
        )
        st.followed_track = followed_track_id(snapshot)
        if st.followed_track is not None:
            st.permanence_seconds = snapshot.stays_seconds.get(
                st.followed_track, 0.0
            )
        st.risk_text = snapshot.risk_text
        st.frames_processed = snapshot.frames_processed
        st.persons_detected = snapshot.persons_detected

        if snapshot.latest_alert is not None:
            st.latest_risk_score = snapshot.latest_alert.risk_score
            self._add_alert(snapshot.latest_alert)
        if snapshot.latest_evidence_path:
            self._add_evidence(snapshot.latest_evidence_path)

    def _add_alert(self, alert) -> None:
        entry = {
            "alert_id": alert.alert_id,
            "event_id": alert.event_id,
            "risk_score": alert.risk_score,
            "created_at": alert.created_at,
        }
        ids = [a["alert_id"] for a in self._state.alert_log]
        if entry["alert_id"] not in ids:
            self._state.alert_log.append(entry)
            if len(self._state.alert_log) > 8:
                self._state.alert_log.pop(0)

    def _add_evidence(self, path: str) -> None:
        if path not in self._state.evidence_paths:
            self._state.evidence_paths.append(path)
            if len(self._state.evidence_paths) > 8:
                self._state.evidence_paths.pop(0)

    def poll_visual(self):
        """Devuelve el último snapshot visual disponible o None."""
        try:
            return self._visual_queue.get_nowait()
        except queue.Empty:
            return None

    def _focus_worker_loop(self):
        while not self._stop_focus_worker:
            with self._focus_condition:
                while self._pending_focus_intent is None and not self._stop_focus_worker:
                    self._focus_condition.wait()
                if self._stop_focus_worker:
                    break
                intent = self._pending_focus_intent
                self._pending_focus_intent = None
                self._active_focus_intent = intent
            
            if hasattr(self, "_manager") and self._manager is not None:
                for cam in self.camera_ids:
                    if intent is not None and cam == intent:
                        self._manager.switch_stream(cam, 0, max_width=0)  # MAIN
                    else:
                        self._manager.switch_stream(cam, 1, max_width=640)  # SUB

            with self._focus_condition:
                self._active_focus_intent = None

    def set_focus(self, camera_id: Optional[str]) -> None:
        """Cambia el foco visual y ajusta el perfil de stream RTSP.
        
        Schedules the transition in a single background worker to prevent
        blocking the Tk event loop. Latest intent wins.
        """
        with self._focus_condition:
            self._pending_focus_intent = camera_id
            self._focus_condition.notify_all()

    def poll_state(self) -> dict:
        """Copia del estado actual para la vista (hilo principal)."""
        with self._lock:
            return {
                "status": self._state.status,
                "source_kind": self._state.source_kind,
                "source_type": self._state.source_type,
                "source_state": self._state.source_state,
                "resolution": self._state.resolution,
                "fps": self._state.fps,
                "source_path_display": self._state.source_path_display,
                "zone_id": self._state.zone_id,
                "zone_name": self._state.zone_name,
                "followed_track": self._state.followed_track,
                "permanence_seconds": self._state.permanence_seconds,
                "risk_text": self._state.risk_text,
                "latest_risk_score": self._state.latest_risk_score,
                "alert_log": list(self._state.alert_log),
                "evidence_paths": list(self._state.evidence_paths),
                "frames_processed": self._state.frames_processed,
                "persons_detected": self._state.persons_detected,
                "error": self._state.error,
                "final_status": self._state.final_status,
            }

    def stop(self) -> None:
        """Solicita la detención del pipeline en curso."""
        self._stop.set()

    def join(self, timeout: Optional[float] = None) -> None:
        """Espera a que termine el hilo de trabajo."""
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout)

    def close(self) -> None:
        """Detiene, espera y limpia sin forzar procesos."""
        self._stop.set()
        if hasattr(self, "_focus_condition"):
            with self._focus_condition:
                self._stop_focus_worker = True
                self._focus_condition.notify_all()
        self.join(timeout=10.0)
        self._drain_visual()
        with self._lock:
            self._state.status = AppStatus.STOPPED

    def _drain_visual(self) -> None:
        while True:
            try:
                self._visual_queue.get_nowait()
            except queue.Empty:
                break
