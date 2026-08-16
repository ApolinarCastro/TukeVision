"""Fuentes de video en vivo para TukeVision.

Responsabilidad única: entregar fotogramas y metadatos desde una webcam
local o una transmisión RTSP, manteniendo una interfaz común equivalente
a VideoSource (open / read / close / metadata / is_open).

El núcleo del pipeline no conoce el origen de los fotogramas.
"""

import logging
import os
import sys
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Generator, Optional, Tuple

import cv2

# Reducir verbosidad de FFmpeg usado por OpenCV para RTSP.
# Esto minimiza (pero no garantiza eliminar) salida en stderr nativo.
os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "quiet")

from src.capture.video_source import (
    VideoMetadata,
    VideoSourceError,
    VideoReadError,
)
from src.observability.logging_setup import redact_rtsp_url

logger = logging.getLogger("tukevision.capture")


def _flush_stderr_safely() -> None:
    """Vacía sys.stderr sin propagar fallos del manejador nativo.

    En ciertos estados del manejador de stderr (p. ej. OSError WinError 1),
    flush() puede lanzar. Un fallo aquí no debe abortar la redirección ni la
    restauración de fd 2, ni enmascarar la excepción del bloque yield.
    """
    try:
        sys.stderr.flush()
    except Exception as exc:
        logger.debug("STDERR_FLUSH_FAILED err=%r", exc)


@contextmanager
def _suppress_native_stderr():
    """Suprime temporalmente stderr a nivel de descriptor de archivo (fd 2).

    FFmpeg (usado por OpenCV para RTSP) escribe directamente en fd 2,
    eludiendo sys.stderr de Python. Esta redirección captura/silencia
    cualquier salida nativa durante operaciones críticas de VideoCapture.

    Context manager exception-safe (LOOP-0018D): un fallo de sys.stderr.flush()
    nunca interrumpe la restauración de fd 2, no deja handles abiertos ni
    reemplaza la excepción del bloque yield. Restituye siempre el estado
    original mediante try/finally.
    """
    original_stderr_fd = -1
    devnull_fd = -1
    try:
        original_stderr_fd = os.dup(2)
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, 2)
        _flush_stderr_safely()
        yield
    finally:
        _flush_stderr_safely()
        if original_stderr_fd != -1:
            try:
                os.dup2(original_stderr_fd, 2)
            except OSError as exc:
                logger.warning("STDERR_FD2_RESTORE_FAILED err=%r", exc)
        for fd in (original_stderr_fd, devnull_fd):
            if fd == -1:
                continue
            try:
                os.close(fd)
            except OSError as exc:
                logger.debug("STDERR_TEMP_FD_CLOSE_FAILED fd=%s err=%r", fd, exc)


def _create_capture_with_suppressed_stderr(
    rtsp_url: str, factory, params: Optional[list] = None
) -> cv2.VideoCapture:
    """Crea y abre VideoCapture suprimiendo stderr nativo durante la operación.

    `params` son pares [propId, valor, ...] que solo se aplican EN LA APERTURA
    (open-only), nunca con set() después de abrir.
    """
    with _suppress_native_stderr():
        if params:
            cap = factory(rtsp_url, cv2.CAP_FFMPEG, params)
        else:
            cap = factory(rtsp_url)
    return cap


class WebcamUnavailableError(VideoSourceError):
    """La webcam solicitada no está disponible."""
    pass


class RTSPSourceError(VideoSourceError):
    """La fuente RTSP no pudo conectarse."""
    pass


class SourceState:
    """Estados técnicos simples de una fuente en vivo."""
    CLOSED = "CLOSED"
    CONNECTING = "CONNECTING"
    OPEN = "OPEN"
    READING = "READING"
    STALLED = "STALLED"
    RECONNECTING = "RECONNECTING"
    FAILED = "FAILED"


class WebcamSource:
    """Fuente de video desde una cámara local (webcam).

    No asume que la webcam existe. open() lanza WebcamUnavailableError
    si no se puede abrir. Entrega fotogramas uno por uno sin acumularlos.
    """

    def __init__(
        self,
        camera_index: int = 0,
        max_width: int = 640,
        process_every_n_frames: int = 1,
        backend: Optional[int] = None,
        capture_factory: Optional[Callable[..., cv2.VideoCapture]] = None,
    ) -> None:
        self._camera_index = camera_index
        self._max_width = max_width
        self._process_every_n_frames = max(1, process_every_n_frames)
        self._backend = backend
        self._capture_factory = capture_factory or cv2.VideoCapture
        self._cap: Optional[cv2.VideoCapture] = None
        self._metadata: Optional[VideoMetadata] = None
        self._frame_index = 0
        self._readable_frames = 0
        self._state = SourceState.CLOSED

    def open(self) -> VideoMetadata:
        """Abre la webcam y valida que se pueda leer un fotograma."""
        self.close()

        self._state = SourceState.CONNECTING
        if self._backend is None:
            self._cap = self._capture_factory(self._camera_index)
        else:
            self._cap = self._capture_factory(self._camera_index, self._backend)

        if self._cap is None or not self._cap.isOpened():
            self._release_capture()
            self._state = SourceState.FAILED
            raise WebcamUnavailableError(
                f"Webcam no disponible (camera_index={self._camera_index})"
            )

        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 0.0)

        ret, _ = self._cap.read()
        if not ret:
            self._release_capture()
            self._state = SourceState.FAILED
            raise VideoReadError("No se puede leer ningún fotograma de la webcam")

        self._metadata = VideoMetadata(
            width=width,
            height=height,
            fps=fps,
            total_frames=0,
            duration_seconds=0.0,
            path=f"WEBCAM:{self._camera_index}",
            source_type="WEBCAM",
        )
        self._frame_index = 0
        self._readable_frames = 0
        self._state = SourceState.OPEN
        return self._metadata

    def read(self) -> Optional[Tuple[int, cv2.typing.MatLike]]:
        """Lee el siguiente fotograma procesado o None si terminó."""
        if self._cap is None or not self._cap.isOpened():
            raise VideoSourceError("La webcam no está abierta. Llame a open() primero.")

        ret, frame = self._cap.read()
        if not ret:
            return None

        if self._frame_index % self._process_every_n_frames != 0:
            self._frame_index += 1
            return self.read()

        processed = self._resize_if_needed(frame)
        index = self._frame_index
        self._frame_index += 1
        self._readable_frames += 1
        return (index, processed)

    def frames(self) -> Generator[Tuple[int, cv2.typing.MatLike], None, None]:
        """Genera fotogramas uno por uno hasta que la cámara termina."""
        if self._cap is None or not self._cap.isOpened():
            raise VideoSourceError("La webcam no está abierta. Llame a open() primero.")

        while True:
            result = self.read()
            if result is None:
                break
            yield result

    def _resize_if_needed(self, frame: cv2.typing.MatLike) -> cv2.typing.MatLike:
        if self._max_width <= 0:
            return frame
        h, w = frame.shape[:2]
        if w <= self._max_width:
            return frame
        scale = self._max_width / w
        return cv2.resize(
            frame, (self._max_width, int(h * scale)), interpolation=cv2.INTER_AREA
        )

    def _release_capture(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def close(self) -> None:
        self._release_capture()
        self._metadata = None
        self._state = SourceState.CLOSED

    @property
    def metadata(self) -> Optional[VideoMetadata]:
        return self._metadata

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def source_type(self) -> str:
        return "WEBCAM"

    @property
    def is_live(self) -> bool:
        return True

    @property
    def state(self) -> str:
        return self._state

    @property
    def readable_frames(self) -> int:
        return self._readable_frames

    def __enter__(self) -> "WebcamSource":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class RTSPSource:
    """Fuente de video desde una transmisión RTSP con endurecimiento de liveness.

    La URL se recibe externamente (argumento o variable de entorno).
    Nunca se almacena en código, tests ni configuración versionada.

    Arquitectura de vigilancia (LOOP-0018B + E01_COMPAT):
      Capture Reader (hilo controlado)  ->  cola FIFO acotada  ->  RTSPSource
      state machine  ->  Pipeline.

      - La lectura real (cap.read()) vive en un hilo de captura controlado
        (_reader_loop). El supervisor (read()) nunca llama a cap.read()
        directamente, de modo que una lectura bloqueada en el backend no
        cuelga al pipeline.
      - El reader publica fotogramas en una COLA FIFO ACOTADA (con
        backpressure: si la cola está llena, el reader espera). El supervisor
        consume en orden: cada fotograma leído se entrega exactamente una vez
        y en orden (contrato de entrega BASE preservado, sin latest-wins).
      - last_valid_frame_at se actualiza SOLO cuando ret==True y frame válido
        (reloj monotónico). No lo actualizan isOpened(), TCP conectado,
        metadata ni reconexiones.
      - Si no hay progreso válido durante frame_stall_timeout_s:
        FRAME_STALL_DETECTED -> captura considerada unhealthy -> reconexión.
      - CAP_PROP_OPEN_TIMEOUT_MSEC se aplica SOLO en la apertura (open-only).
        CAP_PROP_READ_TIMEOUT_MSEC NO se aplica: verificado que rompe la
        apertura RTSP en este build; la cota de lectura la garantiza el
        watchdog de stall (frame_stall_timeout_s).

    Política de reconexión (LOOP-0018A, restaurada como presupuesto global):
      _reconnect_count es un PRESUPUESTO GLOBAL MONOTÓNICO. Cada intento
      físico de apertura lo incrementa una sola vez y NUNCA se reinicia al
      instalar una captura con éxito (invariante E01_COMPAT, corrige el bucle
      infinito de LOOP-0018M). Agotamiento => FAILED + STREAM_LOST.

    Invariante de ownership (LOOP-0018K FASE D):
      El READER es el único dueño de la captura. cap.release() se ejecuta solo
      en el finally del reader. El supervisor jamás libera una captura
      mientras un reader pueda estar dentro de cap.read() sobre esa instancia
      (anti doble-free 0xC0000374).
    """

    _READER_THREAD_NAME = "tukevision-rtsp-reader"
    _READER_JOIN_TIMEOUT_S = 3.0
    _QUEUE_MAX = 8

    def __init__(
        self,
        rtsp_url: str,
        max_width: int = 640,
        process_every_n_frames: int = 1,
        max_reconnect_attempts: int = 3,
        reconnect_delay_seconds: float = 2.0,
        max_open_attempts: int = 3,
        open_retry_delay_seconds: float = 2.0,
        rtsp_open_timeout_ms: int = 8000,
        rtsp_read_timeout_ms: int = 4000,
        frame_stall_timeout_s: float = 10.0,
        capture_factory: Optional[Callable[..., cv2.VideoCapture]] = None,
    ) -> None:
        self._rtsp_url = rtsp_url
        # Trazado seguro de URL RTSP (LOOP-0015-TRACE)
        RTSP_SOURCE_URL_REDACTED = redact_rtsp_url(rtsp_url) if rtsp_url else ""
        if RTSP_SOURCE_URL_REDACTED:
            logger.info("RTSP_SOURCE_URL_REDACTED=%s", RTSP_SOURCE_URL_REDACTED)
        self._max_width = max_width
        self._process_every_n_frames = max(1, process_every_n_frames)
        self._max_reconnect_attempts = max(0, int(max_reconnect_attempts))
        self._reconnect_delay_seconds = max(0.0, float(reconnect_delay_seconds))
        self._max_open_attempts = max(1, int(max_open_attempts))
        self._open_retry_delay_seconds = max(0.0, float(open_retry_delay_seconds))
        self._rtsp_open_timeout_ms = max(0, int(rtsp_open_timeout_ms))
        self._rtsp_read_timeout_ms = max(0, int(rtsp_read_timeout_ms))
        self._frame_stall_timeout_s = max(0.1, float(frame_stall_timeout_s))
        self._capture_factory = capture_factory or cv2.VideoCapture
        if self._rtsp_read_timeout_ms:
            logger.info(
                "RTSP_READ_TIMEOUT_MSEC_UNSUPPORTED read_budget_ms=%s "
                "frame_stall_timeout_s=%s",
                self._rtsp_read_timeout_ms,
                self._frame_stall_timeout_s,
            )

        # Estado compartido entre supervisor (hilo del pipeline) y reader.
        self._cond = threading.Condition()
        self._cap: Optional[cv2.VideoCapture] = None
        self._metadata: Optional[VideoMetadata] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._reader_alive = False
        self._reader_failed = False
        self._abort_reader = False
        self._frame_seq = 0
        self._frame_index = 0
        self._frame_queue: deque = deque()
        self._readable_frames = 0
        self._reconnect_count = 0
        self._last_valid_frame_at = 0.0
        self._stall_count = 0
        self._read_timeout_aborts = 0
        self._state = SourceState.CLOSED

    def open(self) -> VideoMetadata:
        """Conecta a la transmisión RTSP con reintentos acotados (E1).

        Aplica CAP_PROP_OPEN_TIMEOUT_MSEC en la apertura (open-only) y exige
        un frame real para declarar éxito.
        """
        self.close()

        last_error: Optional[Exception] = None
        for attempt in range(1, self._max_open_attempts + 1):
            logger.info("RECONNECT_ATTEMPT=%s", attempt)
            with self._cond:
                self._state = SourceState.CONNECTING
            cap = self._create_capture()

            if cap is None or not cap.isOpened():
                last_error = RTSPSourceError("No se pudo conectar a la fuente RTSP")
                self._safe_release(cap)
                if attempt < self._max_open_attempts:
                    time.sleep(self._open_retry_delay_seconds)
                continue

            ret, _ = self._validate_frame(cap)
            if not ret:
                last_error = VideoReadError(
                    "No se pudo leer ningún fotograma de la fuente RTSP"
                )
                self._safe_release(cap)
                if attempt < self._max_open_attempts:
                    time.sleep(self._open_retry_delay_seconds)
                continue

            # Éxito real: se leyó al menos un frame (E3).
            logger.info("RECONNECT_SUCCESS")
            if not self._install_capture(cap):
                raise RTSPSourceError(
                    "No se pudo conectar a la fuente RTSP tras reintentos"
                )
            return self._metadata

        # Agotados los reintentos de apertura
        logger.info("RECONNECT_EXHAUSTED")
        with self._cond:
            self._state = SourceState.FAILED
        if last_error:
            raise last_error
        raise RTSPSourceError("No se pudo conectar a la fuente RTSP tras reintentos")

    def _create_capture(self) -> Optional[cv2.VideoCapture]:
        """Crea la captura aplicando OPEN_TIMEOUT solo en la apertura.

        READ_TIMEOUT no se aplica (verificado: rompe open() RTSP en este build).
        """
        params = None
        open_prop = getattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC", None)
        if open_prop is not None and self._rtsp_open_timeout_ms > 0:
            params = [open_prop, int(self._rtsp_open_timeout_ms)]
        return _create_capture_with_suppressed_stderr(
            self._rtsp_url, self._capture_factory, params
        )

    @staticmethod
    def _validate_frame(cap) -> Tuple[bool, Optional[cv2.typing.MatLike]]:
        """Lee UN frame real de la captura (o devuelve fallo)."""
        try:
            with _suppress_native_stderr():
                ret, frame = cap.read()
        except Exception:
            return (False, None)
        if ret and frame is not None:
            return (True, frame)
        return (False, None)

    def _install_capture(self, cap: cv2.VideoCapture) -> bool:
        """Instala una captura ya validada y arranca su hilo de lectura.

        NO reinicia _reconnect_count: el presupuesto global de reconexión es
        monotónico (invariante E01_COMPAT, LOOP-0018M).
        """
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)

        thread = threading.Thread(
            target=self._reader_loop,
            args=(cap,),
            daemon=True,
            name=self._READER_THREAD_NAME,
        )
        with self._cond:
            if self._state == SourceState.CLOSED:
                cancelled = True
            else:
                cancelled = False
                self._cap = cap
                self._reader_thread = thread
                self._reader_alive = True
                self._reader_failed = False
                self._abort_reader = False
                self._frame_seq = 0
                self._frame_index = 0
                self._frame_queue.clear()
                self._readable_frames = 0
                self._last_valid_frame_at = time.monotonic()
                self._metadata = VideoMetadata(
                    width=width,
                    height=height,
                    fps=fps,
                    total_frames=0,
                    duration_seconds=0.0,
                    path=redact_rtsp_url(self._rtsp_url),
                    source_type="RTSP",
                )
                self._state = SourceState.OPEN
        if cancelled:
            self._safe_release(cap)
            return False
        thread.start()
        return True

    def read(self) -> Optional[Tuple[int, cv2.typing.MatLike]]:
        """Devuelve el siguiente fotograma procesado o None.

        El supervisor consume la cola FIFO del reader en orden (contrato BASE).
        Si el reader está vivo pero no entrega progreso válido dentro de
        frame_stall_timeout_s: FRAME_STALL_DETECTED -> reconexión controlada.
        """
        while True:
            with self._cond:
                if self._state == SourceState.FAILED:
                    return None
                if self._state == SourceState.CLOSED:
                    raise VideoSourceError(
                        "La fuente RTSP no está abierta. Llame a open() primero."
                    )

                # Fotograma disponible en orden FIFO (contrato BASE).
                if self._frame_queue:
                    _seq, index, frame = self._frame_queue.popleft()
                    self._cond.notify_all()  # reader esperando por espacio
                    if index % self._process_every_n_frames != 0:
                        continue
                    self._readable_frames += 1
                    return (index, self._resize_if_needed(frame))

                # Sin captura válida o reader sin progreso -> reconectar.
                if self._cap is None or not self._reader_alive:
                    reconnect_now = True
                else:
                    age = time.monotonic() - self._last_valid_frame_at
                    if age >= self._frame_stall_timeout_s:
                        self._emit_stall(age)
                        reconnect_now = True
                    else:
                        remaining = self._frame_stall_timeout_s - age
                        self._cond.wait(timeout=remaining)
                        reconnect_now = False

            if not reconnect_now:
                # La espera terminó sin necesidad de reconectar: re-evaluar.
                continue

            ok = self._reconnect()
            if ok:
                continue
            with self._cond:
                if self._state == SourceState.CLOSED:
                    raise VideoSourceError(
                        "La fuente RTSP no está abierta. Llame a open() primero."
                    )
                self._state = SourceState.FAILED
                self._cond.notify_all()
            return None

    def _emit_stall(self, age: float) -> None:
        """Registra la detección de stall. Se invoca con _cond adquirido."""
        self._stall_count += 1
        self._state = SourceState.STALLED
        logger.info(
            "FRAME_STALL_DETECTED LAST_VALID_FRAME_AGE_MS=%d",
            int(age * 1000),
        )
        if self._reader_alive:
            self._read_timeout_aborts += 1
            logger.info(
                "RTSP_READ_TIMEOUT reader_blocked_age_ms=%d",
                int(age * 1000),
            )

    def _reader_loop(self, cap: cv2.VideoCapture) -> None:
        """Hilo de captura controlado: único llamador de cap.read().

        Publica fotogramas en la cola FIFO acotada con sello monotónico y
        avisa al supervisor. Si cap.read() no retorna (backend RTSP bloqueado),
        el supervisor desbloquea llamando cap.release(); read() aborta y el
        hilo termina.

        INVARIANTE LOOP-0018K (FASE D): este hilo es el ÚNICO que libera la
        captura (cap.release() en el finally). Nunca ocurre release() desde
        otro hilo mientras un reader pueda estar ejecutando cap.read() sobre
        esta instancia (anti doble-free 0xC0000374).
        """
        my_thread = threading.current_thread()
        reason = None  # 'failed' | 'error' | 'aborted'
        try:
            while True:
                with self._cond:
                    if self._abort_reader:
                        reason = "aborted"
                        break
                try:
                    with _suppress_native_stderr():
                        ret, frame = cap.read()
                except Exception:
                    # read() interrumpido por release() del supervisor.
                    reason = "error"
                    break
                with self._cond:
                    if self._abort_reader:
                        reason = "aborted"
                        break
                    if not ret or frame is None:
                        reason = "failed"
                        break
                    # Backpressure acotada: esperar espacio en la cola FIFO.
                    while (
                        len(self._frame_queue) >= self._QUEUE_MAX
                        and not self._abort_reader
                    ):
                        self._cond.wait()
                    if self._abort_reader:
                        reason = "aborted"
                        break
                    self._frame_seq += 1
                    self._frame_queue.append(
                        (self._frame_seq, self._frame_index, frame)
                    )
                    self._frame_index += 1
                    self._last_valid_frame_at = time.monotonic()
                    self._cond.notify_all()
        finally:
            # LOOP-0018K (FASE D): el reader es el UNICO que libera la captura.
            try:
                cap.release()
            except Exception:
                pass
            with self._cond:
                if self._reader_thread is my_thread:
                    if reason in ("failed", "error"):
                        self._reader_failed = True
                    self._reader_alive = False
                self._cond.notify_all()

    def _reconnect(self) -> bool:
        """Reconexión física acotada (LOOP-0018A + liveness, contrato BASE).

        _reconnect_count es un PRESUPUESTO GLOBAL MONOTÓNICO: cada intento
        físico de apertura lo incrementa una sola vez y NUNCA se reinicia
        al instalar una captura con éxito (invariante E01_COMPAT).

        Al igual que el BASE, la reconexión NO consume un frame de validación:
        el lector entrega TODOS los frames de la captura nueva (contrato de
        entrega BASE). Si la captura abre pero no produce frames, el reader
        falla y el presupuesto global se agota sin bucle infinito.
        """
        with self._cond:
            if self._reconnect_count >= self._max_reconnect_attempts:
                logger.info("RECONNECT_EXHAUSTED")
                self._state = SourceState.FAILED
                self._cond.notify_all()
                return False
            self._reconnect_count += 1
            logger.info("RECONNECT_ATTEMPT=%s", self._reconnect_count)
            self._state = SourceState.RECONNECTING

        self._shutdown_reader()
        time.sleep(self._reconnect_delay_seconds)

        cap = self._create_capture()
        if cap is None or not cap.isOpened():
            self._safe_release(cap)
            logger.info("RECONNECT_FAILED")
            return False

        if not self._install_capture(cap):
            return False
        logger.info("RECONNECT_SUCCESS")
        return True

    def _shutdown_reader(self) -> None:
        """Detiene el hilo de captura actual sin liberar la captura desde aquí.

        Invariante LOOP-0018K (FASE D): NO se ejecuta cap.release() desde este
        hilo mientras el reader pueda estar dentro de cap.read(). El reader es
        el único dueño de la captura y la libera en su propio finally.

        Si el reader está bloqueado en cap.read() (backend RTSP sin READ
        timeout en este build) y no sale dentro del join timeout, la captura
        queda HUÉRFANA (no se libera desde otro hilo para evitar el doble-free
        0xC0000374) y se registra RTSP_READER_THREAD_STUCK: es un leak acotado,
        preferible a corromper el heap. El siguiente reconnect usa una captura
        nueva.
        """
        with self._cond:
            self._abort_reader = True
            self._cap = None
            self._cond.notify_all()
        thread = self._reader_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=self._READER_JOIN_TIMEOUT_S)
            if thread.is_alive():
                logger.warning("RTSP_READER_THREAD_STUCK")
        self._reader_thread = None

    def frames(self) -> Generator[Tuple[int, cv2.typing.MatLike], None, None]:
        """Genera fotogramas uno por uno hasta que la transmisión termina."""
        if self._state == SourceState.CLOSED:
            raise VideoSourceError(
                "La fuente RTSP no está abierta. Llame a open() primero."
            )
        while True:
            result = self.read()
            if result is None:
                break
            yield result

    def _resize_if_needed(self, frame: cv2.typing.MatLike) -> cv2.typing.MatLike:
        if self._max_width <= 0:
            return frame
        h, w = frame.shape[:2]
        if w <= self._max_width:
            return frame
        scale = self._max_width / w
        return cv2.resize(
            frame, (self._max_width, int(h * scale)), interpolation=cv2.INTER_AREA
        )

    def _safe_release(self, cap: Optional[cv2.VideoCapture]) -> None:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

    def close(self) -> None:
        """Detiene el reader, libera la captura y limpia sin hilos huérfanos."""
        with self._cond:
            self._state = SourceState.CLOSED
            self._cond.notify_all()
        self._shutdown_reader()
        self._metadata = None

    @property
    def metadata(self) -> Optional[VideoMetadata]:
        return self._metadata

    @property
    def is_open(self) -> bool:
        with self._cond:
            return self._cap is not None and self._cap.isOpened()

    @property
    def source_type(self) -> str:
        return "RTSP"

    @property
    def is_live(self) -> bool:
        return True

    @property
    def state(self) -> str:
        with self._cond:
            return self._state

    @property
    def readable_frames(self) -> int:
        return self._readable_frames

    @property
    def last_valid_frame_age_ms(self) -> int:
        """Edad del último frame válido (reloj monotónico)."""
        if not self._last_valid_frame_at:
            return 0
        return int((time.monotonic() - self._last_valid_frame_at) * 1000)

    @property
    def stall_count(self) -> int:
        """Número de detecciones FRAME_STALL_DETECTED acumuladas."""
        return self._stall_count

    @property
    def read_timeout_aborts(self) -> int:
        """Número de lecturas bloqueadas abortadas por el supervisor."""
        return self._read_timeout_aborts

    def __enter__(self) -> "RTSPSource":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()