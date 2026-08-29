"""SourceManager: orquestación multicámara mínima (LOOP-0018N).

Responsabilidad única: registrar, arrancar, detener, consultar salud y aislar
fallos de N fuentes RTSP en paralelo, reutilizando piezas certificadas del
BASE (RTSPSource E01_COMPAT + rtsp_url.build_rtsp_url). NO sustituye el
pipeline canónico (ARCHITECTURE.md): es la capa de orquestación que permite
que cada cámara tenga su propia captura, su propio estado y su propia cola.

Invariantes (PRODUCT_CORE.md / FIRST_PRODUCT_DELIVERY.md):
  - SOURCE_ISOLATION=YES: cada cámara corre en un hilo de trabajo propio.
  - ONE_CAMERA_FAILURE_DOES_NOT_STOP_OTHERS=YES: un fallo marca solo la salud
    de esa cámara; el resto de trabajos siguen intactos.
  - NO_SHARED_MUTABLE_CAPTURE=YES: cada cámara posee su propio RTSPSource y su
    propia cola FIFO acotada; no hay captura compartida entre cámaras.
  - BOUNDED_QUEUE=YES: cola FIFO por cámara con tope (_QUEUE_MAX); política
    drop-oldest (memoria acotada, sin bloqueo del hilo de captura).
  - SECRET_LEAK=0: las credenciales viven solo en el descriptor en memoria y en
    la URL RTSP resultante; ninguna representación persistida las expone
    (se usa redact_rtsp_url).
  - E-01 INTACTO: este módulo compone RTSPSource sin modificarlo.
"""

import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field, replace
from typing import Callable, Deque, Dict, List, Optional

from src.capture.rtsp_url import build_rtsp_url
from src.capture.video_source import VideoSourceError
from src.observability.logging_setup import redact_rtsp_url

logger = logging.getLogger("tukevision.multicamera")


@dataclass(frozen=True)
class CameraDescriptor:
    """Descriptor de una cámara RTSP registrada en el SourceManager.

    El password solo existe en memoria dentro de este descriptor y en la URL
    RTSP construida; __repr__ lo excluye (SECRET_LEAK=0).
    """

    camera_id: str
    host: str
    channel: int = 1
    subtype: int = 1
    username: str = ""
    password: str = ""
    max_width: int = 640
    process_every_n_frames: int = 1
    frame_stall_timeout_s: float = 10.0
    rtsp_open_timeout_ms: int = 8000

    def __repr__(self) -> str:  # type: ignore[override]
        return (
            f"CameraDescriptor(camera_id={self.camera_id!r}, "
            f"host={self.host!r}, channel={self.channel}, subtype={self.subtype})"
        )

    def build_url(self) -> str:
        """Construye la URL RTSP en memoria (nunca se persiste)."""
        return build_rtsp_url(
            host=self.host,
            username=self.username,
            password=self.password,
            channel=self.channel,
            subtype=self.subtype,
        )


@dataclass(frozen=True)
class CameraHealth:
    """Salud agregada de una cámara (per-camera state)."""

    camera_id: str
    state: str
    source_type: str
    fps: float
    resolution: str
    last_valid_frame_age_ms: int
    stall_count: int
    readable_frames: int
    queue_depth: int
    last_error: str
    healthy: bool


@dataclass
class _CameraRuntime:
    """Estado mutable de una cámara en ejecución (por cámara)."""

    descriptor: CameraDescriptor
    source: Optional[object] = None
    stop_event: Optional[threading.Event] = None
    worker: Optional[threading.Thread] = None
    queue: Deque[tuple] = field(default_factory=deque)
    last_snapshot: Optional[dict] = None
    last_error: str = ""


class SourceManagerError(Exception):
    """Error de operación del SourceManager."""
    pass


class SourceManager:
    """Orquesta N fuentes RTSP independientes con aislamiento de fallos.

    - register_source: valida y registra un descriptor (devuelve camera_id).
    - start: arranca la captura de una cámara en su propio hilo de trabajo.
    - stop/restart: detención limpia y rearranque.
    - health/snapshot: consultas no bloqueantes por cámara.
    - list_sources: inventario de descriptores registrados.
    - isolate_failure: detiene únicamente la cámara fallida.
    - close_all: detención y limpieza completa.
    """

    _QUEUE_MAX = 8
    _WORKER_JOIN_TIMEOUT_S = 5.0
    _RECONNECT_SEMAPHORE = threading.Semaphore(2)  # BLOCK E: max 2 simultaneous reconnects

    def __init__(self, source_factory: Optional[Callable[..., object]] = None) -> None:
        self._lock = threading.RLock()
        self._source_factory = source_factory or _default_rtsp_source
        self._runtimes: Dict[str, _CameraRuntime] = {}
        self._running: Dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Registro e inventario
    # ------------------------------------------------------------------
    def register_source(self, descriptor: CameraDescriptor) -> str:
        """Registra un descriptor de cámara y devuelve su camera_id.

        Fallo si el camera_id ya existe o los campos no son válidos.
        """
        camera_id = (descriptor.camera_id or "").strip()
        if not camera_id:
            raise SourceManagerError("camera_id vacío")
        host = (descriptor.host or "").strip()
        if not host.startswith("rtsp://"):
            raise SourceManagerError(f"host debe ser una URL rtsp:// válida: {host!r}")
        with self._lock:
            if camera_id in self._runtimes:
                raise SourceManagerError(f"cámara ya registrada: {camera_id}")
            self._runtimes[camera_id] = _CameraRuntime(descriptor=descriptor)
            self._running[camera_id] = False
        logger.info("SOURCE_REGISTERED camera_id=%s", camera_id)
        return camera_id

    def list_sources(self) -> List[dict]:
        """Inventario de descriptores registrados (sin credenciales)."""
        with self._lock:
            return [
                {
                    "camera_id": cam_id,
                    "host": redact_rtsp_url(rt.descriptor.build_url()),
                    "channel": rt.descriptor.channel,
                    "subtype": rt.descriptor.subtype,
                    "running": bool(self._running.get(cam_id, False)),
                }
                for cam_id, rt in sorted(self._runtimes.items())
            ]

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def start(self, camera_id: str) -> None:
        """Arranca la captura de una cámara en su propio hilo de trabajo."""
        rt = self._get_runtime(camera_id)
        with self._lock:
            if self._running.get(camera_id, False):
                raise SourceManagerError(f"cámara ya en ejecución: {camera_id}")

            stop_event = threading.Event()
            worker = threading.Thread(
                target=self._worker,
                args=(camera_id, rt, stop_event),
                daemon=True,
                name=f"tukevision-multi-{camera_id}",
            )
            rt.stop_event = stop_event
            rt.worker = worker
            rt.queue.clear()
            rt.last_snapshot = None
            rt.last_error = ""
            self._running[camera_id] = True
            worker.start()

    def stop(self, camera_id: str) -> None:
        """Detiene limpiamente la captura de una cámara (solo esa cámara)."""
        rt = self._get_runtime(camera_id)
        stop_event = rt.stop_event
        worker = rt.worker
        if stop_event is not None:
            stop_event.set()
        if worker is not None and worker.is_alive():
            worker.join(timeout=self._WORKER_JOIN_TIMEOUT_S)
        with self._lock:
            rt.stop_event = None
            rt.worker = None
            self._running[camera_id] = False
        logger.info("SOURCE_STOPPED camera_id=%s", camera_id)

    def restart(self, camera_id: str) -> None:
        """stop + start de una cámara (aislado del resto)."""
        self.stop(camera_id)
        self.start(camera_id)

    def switch_stream(self, camera_id: str, subtype: int) -> bool:
        """Cambia subtype (0 MAIN / 1 SUB) para una cámara y la reinicia.

        BLOCK B dual stream: GRID -> SUB, FOCUS -> MAIN. Retorna True si hubo
        cambio, False si ya estaba en ese subtype. Reinicio aislado.
        """
        rt = self._get_runtime(camera_id)
        with self._lock:
            cur = int(rt.descriptor.subtype)
            if cur == int(subtype):
                return False
            rt.descriptor = replace(rt.descriptor, subtype=int(subtype))
        self.restart(camera_id)
        logger.info("STREAM_SWITCH camera_id=%s subtype=%s", camera_id, subtype)
        return True

    def start_all_staggered(self, delay_s: float = 0.35) -> None:
        """Arranca todas las cámaras con delay escalonado (BLOCK H)."""
        with self._lock:
            ids = sorted(self._runtimes.keys())
        for idx, cid in enumerate(ids):
            if idx > 0:
                time.sleep(max(0.0, float(delay_s)))
            try:
                self.start(cid)
            except SourceManagerError as exc:
                logger.warning("STAGGERED_START_FAILED camera_id=%s err=%s", cid, exc)

    def isolate_failure(self, camera_id: str) -> None:
        """Aísla la cámara fallida deteniéndola sin afectar a las demás."""
        self.stop(camera_id)
        logger.info("SOURCE_ISOLATED camera_id=%s", camera_id)

    def close_all(self) -> None:
        """Detiene todas las cámaras y limpia el estado de ejecución."""
        with self._lock:
            camera_ids = list(self._running.keys())
        for camera_id in camera_ids:
            try:
                self.stop(camera_id)
            except SourceManagerError:
                pass
        logger.info("SOURCE_MANAGER_CLOSED cameras=%d", len(camera_ids))

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def health(self, camera_id: str) -> CameraHealth:
        """Salud agregada de una cámara (no bloqueante)."""
        rt = self._get_runtime(camera_id)
        with self._lock:
            source = rt.source
            running = bool(self._running.get(camera_id, False))
            queue_depth = len(rt.queue)
            last_error = rt.last_error

        state = "REGISTERED"
        fps = 0.0
        resolution = ""
        last_age_ms = 0
        stall_count = 0
        readable_frames = 0
        source_type = "RTSP"
        if source is not None:
            state = getattr(source, "state", "OPEN") or "OPEN"
            meta = getattr(source, "metadata", None)
            if meta is not None:
                fps = float(getattr(meta, "fps", 0.0) or 0.0)
                resolution = f"{getattr(meta, 'width', 0)}x{getattr(meta, 'height', 0)}"
            last_age_ms = int(getattr(source, "last_valid_frame_age_ms", 0) or 0)
            stall_count = int(getattr(source, "stall_count", 0) or 0)
            readable_frames = int(getattr(source, "readable_frames", 0) or 0)
            source_type = str(getattr(source, "source_type", "RTSP"))

        healthy = running and state not in ("FAILED", "CLOSED")
        return CameraHealth(
            camera_id=camera_id,
            state=state,
            source_type=source_type,
            fps=fps,
            resolution=resolution,
            last_valid_frame_age_ms=last_age_ms,
            stall_count=stall_count,
            readable_frames=readable_frames,
            queue_depth=queue_depth,
            last_error=last_error,
            healthy=healthy,
        )

    def snapshot(self, camera_id: str) -> Optional[dict]:
        """Último fotograma entregado por la cámara + metadatos (o None)."""
        rt = self._get_runtime(camera_id)
        with self._lock:
            return rt.last_snapshot

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------
    def _get_runtime(self, camera_id: str) -> _CameraRuntime:
        with self._lock:
            rt = self._runtimes.get(camera_id)
            if rt is None:
                raise SourceManagerError(f"cámara no registrada: {camera_id}")
            return rt

    def _worker(
        self, camera_id: str, rt: _CameraRuntime, stop_event: threading.Event
    ) -> None:
        """Hilo de captura de UNA cámara (aislado del resto).

        El SourceManager consume source.frames() (supervisor) y publica en una
        cola FIFO acotada por cámara con política drop-oldest. Un fallo marca
        la salud de esta cámara pero NO derriba el runtime global ni a las
        demás cámaras (NO_SHARED_MUTABLE_CAPTURE). Tras una pérdida de stream
        (FAILED / STREAM_LOST) el worker reintenta con backoff acotado y jitter
        para evitar tormentas de reconexión (BLOCK D), en lugar de abandonar
        la cámara para siempre (ROOT_CAUSE_STREAM_STABILITY).
        """
        attempt = 0
        while not stop_event.is_set():
            source = None
            # BLOCK E: central limit for simultaneous reconnects (max 2)
            # Acquire slot for the open attempt; staggered start already spaces initial opens
            acquired = False
            if attempt > 0:
                acquired = self._RECONNECT_SEMAPHORE.acquire(timeout=10)
                if not acquired:
                    logger.warning("RECONNECT_SLOT_TIMEOUT camera_id=%s", camera_id)
            try:
                source = self._source_factory(rt.descriptor)
                with self._lock:
                    rt.source = source
                    rt.last_error = ""
                metadata = source.open()
                attempt = 0

                for frame_index, frame in source.frames():
                    if stop_event.is_set():
                        break
                    if getattr(source, "state", None) == "FAILED":
                        rt.last_error = "STREAM_LOST"
                        break
                    self._publish(rt, camera_id, frame_index, frame, source, metadata)

                if stop_event.is_set():
                    break
                # Si la fuente terminó el generador en FAILED (reconexiones
                # agotadas), registrar la pérdida aunque no se entregó otro frame.
                if rt.last_error == "" and getattr(source, "state", None) == "FAILED":
                    rt.last_error = "STREAM_LOST"
                # Salida limpia (stop) sin error -> terminar.
                if stop_event.is_set() or rt.last_error == "":
                    with self._lock:
                        self._running[camera_id] = False
                    logger.info("SOURCE_WORKER_END camera_id=%s", camera_id)
                    break
            except Exception as exc:  # aislar: el fallo no propaga a otras cámaras
                if stop_event.is_set():
                    break
                rt.last_error = f"{type(exc).__name__}: {exc}"
                logger.error("SOURCE_FAILED camera_id=%s err=%s", camera_id, exc)
            finally:
                try:
                    if source is not None:
                        source.close()  # type: ignore[union-attr]
                except Exception:
                    pass
                with self._lock:
                    rt.source = None
                if acquired:
                    try:
                        self._RECONNECT_SEMAPHORE.release()
                    except Exception:
                        pass
            if stop_event.is_set():
                with self._lock:
                    self._running[camera_id] = False
                logger.info("SOURCE_WORKER_END camera_id=%s", camera_id)
                break
            if rt.last_error == "":
                # Salida limpia sin error (p.ej. frames agotados sin fallo) -> terminar
                with self._lock:
                    self._running[camera_id] = False
                logger.info("SOURCE_WORKER_END camera_id=%s", camera_id)
                break
            attempt += 1
            base = min(30.0, 2.0 * (1.5 ** min(attempt, 6)))
            jitter = random.uniform(0.0, 1.0)
            delay = base + jitter
            logger.info(
                "SOURCE_RETRY camera_id=%s attempt=%s delay_s=%.1f",
                camera_id, attempt, delay,
            )
            if stop_event.wait(timeout=delay):
                with self._lock:
                    self._running[camera_id] = False
                logger.info("SOURCE_WORKER_END camera_id=%s", camera_id)
                break

    def _publish(
        self,
        rt: _CameraRuntime,
        camera_id: str,
        frame_index: int,
        frame,
        source,
        metadata,
    ) -> None:
        """Publica el fotograma en la cola acotada y refresca el snapshot."""
        with self._lock:
            # BOUNDED_QUEUE: FIFO acotada con drop-oldest (memoria acotada).
            if len(rt.queue) >= self._QUEUE_MAX:
                rt.queue.popleft()
            rt.queue.append((frame_index, frame))
            rt.last_snapshot = {
                "camera_id": camera_id,
                "frame_index": frame_index,
                "frame": frame,
                "state": getattr(source, "state", "OPEN"),
                "source_path": redact_rtsp_url(getattr(metadata, "path", "")),
                "fps": float(getattr(metadata, "fps", 0.0) or 0.0),
                "resolution": (
                    f"{getattr(metadata, 'width', 0)}x{getattr(metadata, 'height', 0)}"
                ),
                "timestamp": time.monotonic(),
            }


def _default_rtsp_source(descriptor: CameraDescriptor):
    """Fábrica por defecto: compone RTSPSource E01_COMPAT sin modificarlo.

    Si RTSP_BACKEND=ffmpeg_supervised (env o config), usa FFmpegSupervisedSource
    con supervisión de proceso (ClearCam/Frigate pattern, no GPL copy).
    
    NO silent fallback: if FFmpeg backend requested but instantiation fails,
    startup fails with identifiable error. Logs effective class per camera.
    """
    import os as _os
    backend = _os.environ.get("RTSP_BACKEND", "").strip().lower()
    import logging as _lg
    logger = _lg.getLogger("tukevision.capture")
    
    if backend in ("ffmpeg", "ffmpeg_supervised", "ffmpeg-supervised"):
        try:
            from src.capture.ffmpeg_supervised import FFmpegSupervisedSource
            source = FFmpegSupervisedSource(
                rtsp_url=descriptor.build_url(),
                max_width=descriptor.max_width,
                process_every_n_frames=descriptor.process_every_n_frames,
                frame_stall_timeout_s=descriptor.frame_stall_timeout_s,
                rtsp_open_timeout_ms=descriptor.rtsp_open_timeout_ms,
                username=descriptor.username,
                password=descriptor.password,
            )
            logger.info("SOURCE_CLASS camera_id=%s class=FFmpegSupervisedSource backend=%s", 
                       descriptor.camera_id, backend)
            return source
        except Exception as exc:
            logger.error("FFMPEG_SOURCE_INSTANTIATION_FAILED camera_id=%s err=%s", 
                        descriptor.camera_id, exc)
            raise VideoSourceError(
                f"FFmpeg backend requested but failed to instantiate: {exc}"
            )
    
    # OpenCV backend (default if no RTSP_BACKEND or explicitly opencv)
    from src.capture.live_sources import RTSPSource
    source = RTSPSource(
        rtsp_url=descriptor.build_url(),
        max_width=descriptor.max_width,
        process_every_n_frames=descriptor.process_every_n_frames,
        frame_stall_timeout_s=descriptor.frame_stall_timeout_s,
        rtsp_open_timeout_ms=descriptor.rtsp_open_timeout_ms,
    )
    logger.info("SOURCE_CLASS camera_id=%s class=RTSPSource backend=opencv", 
               descriptor.camera_id)
    return source