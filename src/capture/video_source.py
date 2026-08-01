"""Módulo de captura de video local.

Responsabilidad única: abrir, validar y entregar fotogramas de un archivo de video.
"""

import cv2
from pathlib import Path
from typing import Generator, Optional, Tuple
from dataclasses import dataclass


@dataclass
class VideoMetadata:
    """Metadatos del video."""
    width: int
    height: int
    fps: float
    total_frames: int
    duration_seconds: float
    path: str


class VideoSourceError(Exception):
    """Excepción base para errores de VideoSource."""
    pass


class VideoNotFoundError(VideoSourceError):
    """El archivo de video no existe."""
    pass


class VideoOpenError(VideoSourceError):
    """El archivo no puede abrirse con OpenCV."""
    pass


class VideoReadError(VideoSourceError):
    """No se puede leer ningún fotograma."""
    pass


class VideoSource:
    """Fuente de video local.

    Abre un archivo de video, valida su contenido y entrega fotogramas
    uno por uno con redimensionamiento opcional manteniendo la proporción.
    """

    def __init__(
        self,
        video_path: str,
        max_width: int = 640,
        process_every_n_frames: int = 1
    ) -> None:
        """Inicializa la fuente de video.

        Args:
            video_path: Ruta al archivo de video.
            max_width: Ancho máximo del fotograma (0 = sin límite).
            process_every_n_frames: Procesar 1 de cada N fotogramas.
        """
        self._video_path = Path(video_path)
        self._max_width = max_width
        self._process_every_n_frames = max(1, process_every_n_frames)
        self._cap: Optional[cv2.VideoCapture] = None
        self._metadata: Optional[VideoMetadata] = None
        self._frame_index = 0
        self._readable_frames = 0

    def open(self) -> VideoMetadata:
        """Abre el video y valida su contenido.

        Returns:
            VideoMetadata con información del video.

        Raises:
            VideoNotFoundError: Si el archivo no existe.
            VideoOpenError: Si OpenCV no puede abrir el archivo.
            VideoReadError: Si no se puede leer ningún fotograma.
        """
        if not self._video_path.exists():
            raise VideoNotFoundError(f"El archivo no existe: {self._video_path}")

        if not self._video_path.is_file():
            raise VideoNotFoundError(f"La ruta no es un archivo: {self._video_path}")

        self._cap = cv2.VideoCapture(str(self._video_path))

        if not self._cap.isOpened():
            raise VideoOpenError(f"No se puede abrir el video: {self._video_path}")

        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps <= 0 or total_frames <= 0:
            raise VideoReadError("El video no tiene fotogramas válidos (FPS o total_frames <= 0)")

        duration = total_frames / fps if fps > 0 else 0.0

        # Verificar que se puede leer al menos un fotograma
        ret, _ = self._cap.read()
        if not ret:
            self._cap.release()
            self._cap = None
            raise VideoReadError("No se puede leer ningún fotograma del video")

        # Volver al inicio
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        self._metadata = VideoMetadata(
            width=width,
            height=height,
            fps=fps,
            total_frames=total_frames,
            duration_seconds=duration,
            path=str(self._video_path)
        )
        self._frame_index = 0
        self._readable_frames = 0

        return self._metadata

    def frames(self) -> Generator[Tuple[int, cv2.typing.MatLike], None, None]:
        """Genera fotogramas uno por uno.

        Yields:
            Tupla (índice_del_fotograma, fotograma_redimensionado).

        Raises:
            VideoSourceError: Si el video no está abierto.
        """
        if self._cap is None or not self._cap.isOpened():
            raise VideoSourceError("El video no está abierto. Llame a open() primero.")

        while True:
            ret, frame = self._cap.read()
            if not ret:
                break

            if self._frame_index % self._process_every_n_frames == 0:
                processed_frame = self._resize_if_needed(frame)
                self._readable_frames += 1
                yield (self._frame_index, processed_frame)

            self._frame_index += 1

    def _resize_if_needed(self, frame: cv2.typing.MatLike) -> cv2.typing.MatLike:
        """Reduce el ancho manteniendo la proporción si supera max_width."""
        if self._max_width <= 0:
            return frame

        h, w = frame.shape[:2]
        if w <= self._max_width:
            return frame

        scale = self._max_width / w
        new_w = self._max_width
        new_h = int(h * scale)
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

    @property
    def metadata(self) -> Optional[VideoMetadata]:
        """Devuelve los metadatos del video (None si no está abierto)."""
        return self._metadata

    @property
    def readable_frames(self) -> int:
        """Cantidad de fotogramas leídos (procesados)."""
        return self._readable_frames

    def close(self) -> None:
        """Libera el recurso del video."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "VideoSource":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()