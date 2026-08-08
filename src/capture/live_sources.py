"""Fuentes de video en vivo para TukeVision.

Responsabilidad única: entregar fotogramas y metadatos desde una webcam
local o una transmisión RTSP, manteniendo una interfaz común equivalente
a VideoSource (open / read / close / metadata / is_open).

El núcleo del pipeline no conoce el origen de los fotogramas.
"""

import time
from dataclasses import dataclass
from typing import Callable, Generator, Optional, Tuple

import cv2

from src.capture.video_source import (
    VideoMetadata,
    VideoSourceError,
    VideoReadError,
)


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
    """Fuente de video desde una transmisión RTSP.

    La URL se recibe externamente (argumento o variable de entorno).
    Nunca se almacena en código, tests ni configuración versionada.

    Política de reconexión mínima y acotada:
        lectura falla → cerrar captura → esperar → reintentar conexión.
    Con límite configurable (max_reconnect_attempts, reconnect_delay_seconds).
    """

    def __init__(
        self,
        rtsp_url: str,
        max_width: int = 640,
        process_every_n_frames: int = 1,
        max_reconnect_attempts: int = 3,
        reconnect_delay_seconds: float = 2.0,
        capture_factory: Optional[Callable[..., cv2.VideoCapture]] = None,
    ) -> None:
        self._rtsp_url = rtsp_url
        self._max_width = max_width
        self._process_every_n_frames = max(1, process_every_n_frames)
        self._max_reconnect_attempts = max(0, int(max_reconnect_attempts))
        self._reconnect_delay_seconds = max(0.0, float(reconnect_delay_seconds))
        self._capture_factory = capture_factory or cv2.VideoCapture
        self._cap: Optional[cv2.VideoCapture] = None
        self._metadata: Optional[VideoMetadata] = None
        self._frame_index = 0
        self._readable_frames = 0
        self._reconnect_count = 0
        self._state = SourceState.CLOSED

    def open(self) -> VideoMetadata:
        """Conecta a la transmisión RTSP y valida la lectura inicial."""
        self.close()

        self._state = SourceState.CONNECTING
        self._cap = self._capture_factory(self._rtsp_url)

        if self._cap is None or not self._cap.isOpened():
            self._release_capture()
            self._state = SourceState.FAILED
            raise RTSPSourceError("No se pudo conectar a la fuente RTSP")

        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 0.0)

        ret, _ = self._cap.read()
        if not ret:
            self._release_capture()
            self._state = SourceState.FAILED
            raise VideoReadError("No se pudo leer ningún fotograma de la fuente RTSP")

        # La ruta mostrada nunca incluye credenciales ni IP privada.
        self._metadata = VideoMetadata(
            width=width,
            height=height,
            fps=fps,
            total_frames=0,
            duration_seconds=0.0,
            path="rtsp://[redacted]",
            source_type="RTSP",
        )
        self._frame_index = 0
        self._readable_frames = 0
        self._state = SourceState.OPEN
        return self._metadata

    def read(self) -> Optional[Tuple[int, cv2.typing.MatLike]]:
        """Lee el siguiente fotograma procesado o None al agotar reconexiones."""
        if self._cap is None or not self._cap.isOpened():
            raise VideoSourceError("La fuente RTSP no está abierta. Llame a open() primero.")

        ret, frame = self._cap.read()
        if not ret:
            if self._reconnect():
                return self.read()
            self._state = SourceState.FAILED
            return None

        if self._frame_index % self._process_every_n_frames != 0:
            self._frame_index += 1
            return self.read()

        processed = self._resize_if_needed(frame)
        index = self._frame_index
        self._frame_index += 1
        self._readable_frames += 1
        return (index, processed)

    def _reconnect(self) -> bool:
        """Reintenta la conexión hasta agotar el límite global de reconexiones."""
        if self._reconnect_count >= self._max_reconnect_attempts:
            return False
        self._state = SourceState.RECONNECTING
        self._release_capture()
        time.sleep(self._reconnect_delay_seconds)
        self._reconnect_count += 1
        self._cap = self._capture_factory(self._rtsp_url)
        if self._cap is not None and self._cap.isOpened():
            self._state = SourceState.OPEN
            return True
        self._release_capture()
        return False

    def frames(self) -> Generator[Tuple[int, cv2.typing.MatLike], None, None]:
        """Genera fotogramas uno por uno hasta que la transmisión termina."""
        if self._cap is None or not self._cap.isOpened():
            raise VideoSourceError("La fuente RTSP no está abierta. Llame a open() primero.")

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
        return "RTSP"

    @property
    def is_live(self) -> bool:
        return True

    @property
    def state(self) -> str:
        return self._state

    @property
    def readable_frames(self) -> int:
        return self._readable_frames

    def __enter__(self) -> "RTSPSource":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
