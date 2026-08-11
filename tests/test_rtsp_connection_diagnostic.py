"""Pruebas unitarias del diagnóstico RTSP autorizado.

Solo usa mocks y fixtures locales. No se conecta a Internet ni a ningún
equipo real.
"""

import unittest
from unittest.mock import MagicMock

import numpy as np

from src.capture.video_source import VideoSourceError
from src.diagnostics.rtsp_connection_test import (
    RTSPConnectionTest,
    RTSPDiagnosticResult,
    RTSPFrameState,
    RTSPNetworkState,
    RTSPOpenState,
    RTSPSourceState,
    build_safe_display,
    summarize_result,
)


def _fake_source(
    opened=True,
    fail_open=False,
    frames=None,
    width=640,
    height=480,
    fps=30.0,
):
    """Construye una fuente RTSP simulada con interfaz común."""
    source = MagicMock()
    if frames is None:
        frames = [(i, np.zeros((height, width, 3), dtype=np.uint8)) for i in range(10)]

    if fail_open:
        source.open.side_effect = VideoSourceError("no se pudo conectar")
    else:
        metadata = MagicMock()
        metadata.width = width
        metadata.height = height
        metadata.fps = fps
        source.open.return_value = metadata

    def _read():
        if not opened:
            return None
        if frames:
            return frames.pop(0)
        return None

    source.read.side_effect = _read
    return source


class TestRTSPDiagnosticResult(unittest.TestCase):
    """El resultado es inmutable y no expone credenciales."""

    def test_result_is_frozen(self) -> None:
        result = RTSPDiagnosticResult()
        with self.assertRaises(AttributeError):
            result.frames_received = 99  # type: ignore[misc]

    def test_result_never_contains_url_or_password(self) -> None:
        result = RTSPDiagnosticResult(safe_message="mensaje genérico")
        text = str(result.__dict__)
        self.assertNotIn("rtsp://", text)
        self.assertNotIn("password", text.lower())
        self.assertNotIn("usuario", text.lower())


class TestRTSPConnectionTest(unittest.TestCase):
    """Comportamiento del diagnóstico con fuentes simuladas."""

    def test_explicit_source_accepted(self) -> None:
        """El diagnóstico acepta una fuente RTSP explícita."""
        source = _fake_source()
        test = RTSPConnectionTest(source_factory=lambda url: source)
        result = test.run("rtsp://user:secret@host/stream")
        self.assertIsInstance(result, RTSPDiagnosticResult)
        self.assertEqual(result.stream_open_status, RTSPOpenState.STREAM_OPENED)

    def test_frames_received(self) -> None:
        """Recepción de fotogramas correcta con metadata extraída."""
        source = _fake_source(frames=[(i, np.zeros((480, 640, 3), dtype=np.uint8)) for i in range(5)])
        test = RTSPConnectionTest(source_factory=lambda url: source)
        result = test.run("rtsp://host/stream")
        self.assertEqual(result.frame_status, RTSPFrameState.FRAMES_RECEIVED)
        self.assertEqual(result.frames_received, 5)
        self.assertEqual(result.resolution, "640x480")

    def test_open_failure_classified(self) -> None:
        """Fallo de apertura se clasifica como STREAM_OPEN_FAILED."""
        source = _fake_source(fail_open=True)
        test = RTSPConnectionTest(source_factory=lambda url: source)
        result = test.run("rtsp://host/stream")
        self.assertEqual(result.stream_open_status, RTSPOpenState.STREAM_OPEN_FAILED)
        self.assertEqual(result.error_category, "UNKNOWN_CONNECTION_FAILURE")
        # No se afirma autenticación fallida sin evidencia
        self.assertNotIn("AUTHENTICATION", result.error_category)

    def test_no_frames(self) -> None:
        """Fuente abierta pero sin fotogramas → NO_FRAMES."""
        source = _fake_source(frames=[])
        test = RTSPConnectionTest(source_factory=lambda url: source)
        result = test.run("rtsp://host/stream")
        self.assertEqual(result.frame_status, RTSPFrameState.NO_FRAMES)
        self.assertEqual(result.frames_received, 0)

    def test_bounded_execution(self) -> None:
        """La ejecución está limitada por max_frames."""
        source = _fake_source(frames=[(i, np.zeros((480, 640, 3), dtype=np.uint8)) for i in range(100)])
        test = RTSPConnectionTest(
            source_factory=lambda url: source,
            max_frames=7,
        )
        result = test.run("rtsp://host/stream")
        self.assertLessEqual(result.frames_received, 7)
        self.assertEqual(source.read.call_count, 7)

    def test_timeout_condition(self) -> None:
        """El límite de duración produce TIMEOUT de forma determinística."""
        frames = [(i, np.zeros((480, 640, 3), dtype=np.uint8)) for i in range(100)]

        def _slow_read():
            import time
            time.sleep(0.05)
            if frames:
                return frames.pop(0)
            return None

        source = MagicMock()
        metadata = MagicMock()
        metadata.width = 640
        metadata.height = 480
        metadata.fps = 30.0
        source.open.return_value = metadata
        source.read.side_effect = _slow_read

        test = RTSPConnectionTest(
            source_factory=lambda url: source,
            connect_timeout_seconds=0.1,
            test_duration_seconds=0.15,
            max_frames=1000,
        )
        result = test.run("rtsp://host/stream")
        self.assertEqual(result.frame_status, RTSPFrameState.TIMEOUT)
        self.assertLess(result.elapsed_seconds, 1.0)

    def test_source_always_closed(self) -> None:
        """La fuente se cierra siempre, incluso en fallo de apertura."""
        source = _fake_source(fail_open=True)
        test = RTSPConnectionTest(source_factory=lambda url: source)
        result = test.run("rtsp://host/stream")
        self.assertEqual(result.source_closed, RTSPSourceState.SOURCE_CLOSED)
        source.close.assert_called_once()

    def test_source_closed_on_success(self) -> None:
        """En éxito también se cierra la fuente."""
        source = _fake_source()
        test = RTSPConnectionTest(source_factory=lambda url: source)
        result = test.run("rtsp://host/stream")
        self.assertEqual(result.source_closed, RTSPSourceState.SOURCE_CLOSED)

    def test_credentials_never_exposed_in_result(self) -> None:
        """El resultado no contiene la URL con credenciales ni la contraseña."""
        source = _fake_source()
        test = RTSPConnectionTest(source_factory=lambda url: source)
        result = test.run("rtsp://admin:sup3rsecret@192.168.1.50/stream")
        text = summarize_result(result)
        self.assertNotIn("sup3rsecret", text)
        self.assertNotIn("admin", text)
        self.assertNotIn("192.168.1.50", text)
        self.assertNotIn("rtsp://", text)

    def test_safe_display_redacts_credentials(self) -> None:
        """build_safe_display redacta credenciales de la URL."""
        safe = build_safe_display("rtsp://admin:secret@10.0.0.5/stream")
        self.assertNotIn("secret", safe)
        self.assertIn("REDACTED", safe)

    def test_error_does_not_include_url(self) -> None:
        """El mensaje seguro del fallo no incluye la URL original."""
        source = _fake_source(fail_open=True)
        test = RTSPConnectionTest(source_factory=lambda url: source)
        result = test.run("rtsp://user:clave@host/stream")
        self.assertNotIn("clave", result.safe_message)
        self.assertNotIn("user", result.safe_message)

    def test_single_frame_consumed_on_open(self) -> None:
        """open() consume un fotograma de validación; no rompe la lectura."""
        source = _fake_source(frames=[(i, np.zeros((480, 640, 3), dtype=np.uint8)) for i in range(3)])
        test = RTSPConnectionTest(source_factory=lambda url: source)
        result = test.run("rtsp://host/stream")
        self.assertEqual(result.frames_received, 3)


if __name__ == "__main__":
    unittest.main()
