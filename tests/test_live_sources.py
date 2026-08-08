"""Pruebas unitarias para src.capture.live_sources (webcam y RTSP)."""

import time
import unittest
from unittest.mock import patch

import numpy as np

from src.capture.live_sources import (
    RTSPSource,
    RTSPSourceError,
    SourceState,
    WebcamSource,
    WebcamUnavailableError,
)
from src.capture.video_source import (
    VideoMetadata,
    VideoReadError,
    VideoSourceError,
)


class FakeCapture:
    """Simula cv2.VideoCapture para pruebas controladas."""

    def __init__(
        self,
        opened: bool = True,
        width: int = 640,
        height: int = 480,
        fps: float = 30.0,
        frames: int = 20,
        fail_read: bool = False,
    ) -> None:
        self._opened = opened
        self._width = width
        self._height = height
        self._fps = fps
        self._remaining = frames
        self._fail_read = fail_read
        self._released = False

    def isOpened(self) -> bool:
        return self._opened

    def read(self):
        if not self._opened or self._fail_read or self._remaining <= 0:
            return (False, None)
        self._remaining -= 1
        frame = np.zeros((self._height, self._width, 3), dtype=np.uint8)
        return (True, frame)

    def get(self, prop: int) -> float:
        import cv2
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return self._width
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return self._height
        if prop == cv2.CAP_PROP_FPS:
            return self._fps
        return 0.0

    def release(self) -> None:
        self._released = True
        self._opened = False


def make_factory(capture):
    return lambda *args, **kwargs: capture


class TestWebcamSource(unittest.TestCase):

    def test_open_valid_webcam(self) -> None:
        """Abre una webcam válida simulada y devuelve metadatos."""
        cap = FakeCapture()
        source = WebcamSource(camera_index=0, capture_factory=make_factory(cap))
        metadata = source.open()

        self.assertIsInstance(metadata, VideoMetadata)
        self.assertEqual(metadata.source_type, "WEBCAM")
        self.assertEqual(metadata.width, 640)
        self.assertEqual(metadata.height, 480)
        self.assertAlmostEqual(metadata.fps, 30.0)
        self.assertTrue(source.is_live)
        self.assertTrue(source.is_open)
        source.close()

    def test_open_missing_webcam_raises(self) -> None:
        """Una webcam inexistente produce WebcamUnavailableError."""
        cap = FakeCapture(opened=False)
        source = WebcamSource(camera_index=9, capture_factory=make_factory(cap))
        with self.assertRaises(WebcamUnavailableError):
            source.open()
        self.assertFalse(source.is_open)
        source.close()

    def test_read_frames(self) -> None:
        """Lee fotogramas de la webcam sin acumularlos."""
        cap = FakeCapture(frames=6)
        source = WebcamSource(camera_index=0, capture_factory=make_factory(cap))
        source.open()

        frames = list(source.frames())
        # open() consume un fotograma en la validación de legibilidad
        self.assertEqual(len(frames), 5)
        for idx, frame in frames:
            self.assertIsInstance(frame, np.ndarray)
        self.assertEqual(source.readable_frames, 5)
        source.close()

    def test_close_releases_capture(self) -> None:
        """close() libera el recurso y el estado vuelve a CLOSED."""
        cap = FakeCapture()
        source = WebcamSource(camera_index=0, capture_factory=make_factory(cap))
        source.open()
        source.close()

        self.assertTrue(cap._released)
        self.assertFalse(source.is_open)
        self.assertEqual(source.state, SourceState.CLOSED)

    def test_close_without_open(self) -> None:
        """close() sin open() no falla."""
        source = WebcamSource(camera_index=0)
        source.close()

    def test_metadata_none_before_open(self) -> None:
        """metadata es None antes de abrir."""
        source = WebcamSource(camera_index=0)
        self.assertIsNone(source.metadata)


class TestRTSPSource(unittest.TestCase):

    def test_open_valid_rtsp(self) -> None:
        """Conecta una fuente RTSP válida simulada."""
        cap = FakeCapture()
        source = RTSPSource(
            rtsp_url="rtsp://example.invalid/stream",
            capture_factory=make_factory(cap),
        )
        metadata = source.open()

        self.assertIsInstance(metadata, VideoMetadata)
        self.assertEqual(metadata.source_type, "RTSP")
        self.assertTrue(source.is_live)
        self.assertTrue(source.is_open)
        source.close()

    def test_open_invalid_rtsp_raises(self) -> None:
        """Una conexión RTSP inválida produce RTSPSourceError."""
        cap = FakeCapture(opened=False)
        source = RTSPSource(
            rtsp_url="rtsp://example.invalid/stream",
            capture_factory=make_factory(cap),
        )
        with self.assertRaises(RTSPSourceError):
            source.open()
        source.close()

    def test_metadata_does_not_expose_credentials(self) -> None:
        """La ruta de metadatos RTSP no expone credenciales."""
        cap = FakeCapture()
        source = RTSPSource(
            rtsp_url="rtsp://user:secret@10.0.0.5/stream",
            capture_factory=make_factory(cap),
        )
        metadata = source.open()
        self.assertNotIn("user", metadata.path)
        self.assertNotIn("secret", metadata.path)
        self.assertNotIn("10.0.0.5", metadata.path)
        self.assertEqual(metadata.path, "rtsp://[redacted]")
        source.close()

    def test_read_frames(self) -> None:
        """Lee fotogramas de la fuente RTSP."""
        cap = FakeCapture(frames=9)
        source = RTSPSource(
            rtsp_url="rtsp://example.invalid/stream",
            capture_factory=make_factory(cap),
        )
        source.open()

        frames = list(source.frames())
        # open() consume un fotograma en la validación de legibilidad
        self.assertEqual(len(frames), 8)
        source.close()

    def test_reconnect_on_read_failure(self) -> None:
        """Al fallar la lectura, se reconecta y continúa leyendo."""
        calls = []

        def flaky_factory(*args, **kwargs):
            if not calls:
                calls.append(1)
                # Primera conexión: abre y valida (1 frame), luego se agota
                return FakeCapture(opened=True, frames=1)
            calls.append(1)
            # Reconexión: funciona
            return FakeCapture(opened=True, frames=5)

        source = RTSPSource(
            rtsp_url="rtsp://example.invalid/stream",
            max_reconnect_attempts=1,
            reconnect_delay_seconds=0.0,
            capture_factory=flaky_factory,
        )
        source.open()

        frames = list(source.frames())
        self.assertEqual(len(frames), 5)
        # La reconexión entregó 5 frames; al agotarse la fuente con el
        # límite global alcanzado, el estado final es FAILED.
        self.assertEqual(source.state, SourceState.FAILED)
        source.close()

    def test_reconnect_stops_after_global_limit(self) -> None:
        """Tras una reconexión exitosa, la fuente no vuelve a reconectarse sin límite."""
        calls = []

        def flaky_factory(*args, **kwargs):
            if not calls:
                calls.append(1)
                return FakeCapture(opened=True, frames=1)
            calls.append(1)
            return FakeCapture(opened=True, frames=2)

        source = RTSPSource(
            rtsp_url="rtsp://example.invalid/stream",
            max_reconnect_attempts=1,
            reconnect_delay_seconds=0.0,
            capture_factory=flaky_factory,
        )
        source.open()

        frames = list(source.frames())
        # Tras la reconexión (2 frames), al agotarse no se reintenta más
        self.assertEqual(len(frames), 2)
        self.assertEqual(source._reconnect_count, 1)
        source.close()

    def test_reconnect_limit_exhausted(self) -> None:
        """Al agotar los reintentos, la fuente termina en FAILED."""
        cap = FakeCapture(opened=False)

        source = RTSPSource(
            rtsp_url="rtsp://example.invalid/stream",
            max_reconnect_attempts=2,
            reconnect_delay_seconds=0.0,
            capture_factory=make_factory(cap),
        )
        # open() falla directamente (la primera conexión no abre)
        with self.assertRaises(RTSPSourceError):
            source.open()
        self.assertEqual(source.state, SourceState.FAILED)

    def test_reconnect_failure_during_read(self) -> None:
        """Si la lectura falla y las reconexiones no abren, se termina limpio."""
        def always_closed(*args, **kwargs):
            return FakeCapture(opened=False)

        source = RTSPSource(
            rtsp_url="rtsp://example.invalid/stream",
            max_reconnect_attempts=2,
            reconnect_delay_seconds=0.0,
            capture_factory=always_closed,
        )
        with self.assertRaises(RTSPSourceError):
            source.open()

    def test_close_releases_capture(self) -> None:
        """close() libera el recurso RTSP."""
        cap = FakeCapture()
        source = RTSPSource(
            rtsp_url="rtsp://example.invalid/stream",
            capture_factory=make_factory(cap),
        )
        source.open()
        source.close()
        self.assertTrue(cap._released)
        self.assertEqual(source.state, SourceState.CLOSED)

    def test_metadata_none_before_open(self) -> None:
        """metadata es None antes de abrir."""
        source = RTSPSource(rtsp_url="rtsp://example.invalid/stream")
        self.assertIsNone(source.metadata)


if __name__ == "__main__":
    unittest.main()
