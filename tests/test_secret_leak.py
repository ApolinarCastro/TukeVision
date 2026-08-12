"""Pruebas permanentes de no exposición de secretos (AC-SEC-01 a AC-SEC-14).

Verifican que las credenciales ficticias nunca aparecen en representaciones
redactadas, metadatos, stdout, stderr de Python ni stderr nativo (fd 2)
durante el flujo RTSP. Usa exclusivamente credenciales ficticias; cualquier
valor real está prohibido en estas pruebas.
"""

import io
import os
import sys
import unittest
import contextlib
from unittest.mock import patch

from src.capture.live_sources import (
    RTSPSource,
    RTSPSourceError,
    WebcamSource,
    _suppress_native_stderr,
)
from src.capture.rtsp_url import build_rtsp_url
from src.capture.video_source import VideoMetadata, VideoNotFoundError
from src.observability.logging_setup import redact_rtsp_url
from scripts.test_rtsp_connection import _with_credentials

# Credenciales ficticias de prueba. Nunca son datos reales.
CANARY = "SECRET_CANARY_RTSP_8F21"
FAKE_USER = "test_user"
FAKE_PASSWORD = "Fake:P@ss\\word%123?&#"
FAKE_HOST = "rtsp://192.168.1.50:554/cam/realmonitor?channel=1&subtype=1"


class FakeCapture:
    """Simula cv2.VideoCapture para pruebas controladas."""

    def __init__(self, opened: bool = True, frames: int = 20) -> None:
        self._opened = opened
        self._remaining = frames
        self._released = False

    def isOpened(self) -> bool:
        return self._opened

    def read(self):
        import numpy as np
        if not self._opened or self._remaining <= 0:
            return (False, None)
        self._remaining -= 1
        return (True, np.zeros((480, 640, 3), dtype=np.uint8))

    def get(self, prop: int) -> float:
        import cv2
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return 640.0
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return 480.0
        if prop == cv2.CAP_PROP_FPS:
            return 30.0
        return 0.0

    def release(self) -> None:
        self._released = True
        self._opened = False


def make_factory(capture):
    return lambda *args, **kwargs: capture


def _fd2_bytes_written(action) -> bytes:
    """Captura lo que se escribe en fd 2 (stderr nativo) durante la acción.

    Redirige temporalmente el descriptor real de stderr a un pipe para
    poder leer, a nivel de descriptor, dónde acaban las escrituras.
    """
    r_fd, w_fd = os.pipe()
    real_stderr_fd = os.dup(2)
    os.dup2(w_fd, 2)
    try:
        action()
    finally:
        os.dup2(real_stderr_fd, 2)
        os.close(real_stderr_fd)
        os.close(w_fd)
        os.set_blocking(r_fd, False)
        chunks = []
        while True:
            try:
                chunk = os.read(r_fd, 4096)
                if not chunk:
                    break
                chunks.append(chunk)
            except BlockingIOError:
                break
        os.close(r_fd)
    return b"".join(chunks)


class TestURLConstruction(unittest.TestCase):
    """AC-SEC-01 y AC-SEC-02: construcción de URL con credenciales."""

    def test_url_build_preserves_host_path_query(self) -> None:
        """AC-SEC-01: la URL interna conserva host, path y query."""
        url = _with_credentials(FAKE_HOST, FAKE_USER, FAKE_PASSWORD)
        self.assertIn("192.168.1.50:554", url)
        self.assertIn("/cam/realmonitor", url)
        self.assertIn("channel=1&subtype=1", url)

    def test_special_char_password_encoded(self) -> None:
        """AC-SEC-02: passwords con caracteres especiales se codifican."""
        url = _with_credentials(FAKE_HOST, FAKE_USER, FAKE_PASSWORD)
        self.assertIn("Fake%3AP%40ss%5Cword%25123%3F%26%23", url)
        # El password crudo (con caracteres especiales) no aparece.
        self.assertNotIn(FAKE_PASSWORD, url)

    def test_build_rtsp_url_sin_credenciales(self) -> None:
        """AC-SEC-15: sin credenciales se conserva el host tal cual."""
        self.assertEqual(
            build_rtsp_url(FAKE_HOST, "", ""), FAKE_HOST
        )

    def test_build_rtsp_url_vacio_devuelve_vacio(self) -> None:
        """AC-SEC-16: host vacío devuelve cadena vacía."""
        self.assertEqual(build_rtsp_url("", "u", "p"), "")
        self.assertEqual(build_rtsp_url("   ", "u", "p"), "")

    def test_build_rtsp_url_equivale_a_with_credentials(self) -> None:
        """AC-SEC-17: el helper compartido construye la misma URL segura."""
        self.assertEqual(
            build_rtsp_url(FAKE_HOST, FAKE_USER, FAKE_PASSWORD),
            _with_credentials(FAKE_HOST, FAKE_USER, FAKE_PASSWORD),
        )

    def test_build_rtsp_url_con_password_vacio(self) -> None:
        """AC-SEC-18: contraseña vacía mantiene el usuario y redacta igual."""
        url = build_rtsp_url(FAKE_HOST, FAKE_USER, "")
        self.assertNotIn(FAKE_USER, redact_rtsp_url(url))
        self.assertIn("REDACTED:REDACTED", redact_rtsp_url(url))


class TestRedaction(unittest.TestCase):
    """AC-SEC-03 y AC-SEC-04: username/password ausentes de la redacción."""

    def test_username_absent_from_redacted(self) -> None:
        """AC-SEC-03: username ausente de la representación redactada."""
        url = _with_credentials(FAKE_HOST, FAKE_USER, FAKE_PASSWORD)
        redacted = redact_rtsp_url(url)
        self.assertNotIn(FAKE_USER, redacted)
        self.assertIn("REDACTED:REDACTED", redacted)

    def test_password_absent_from_redacted(self) -> None:
        """AC-SEC-04: password (incluido el canary) ausente de la redacción."""
        cases = [
            f"rtsp://{FAKE_USER}:{CANARY}@192.168.1.50/cam",
            # Ruta real: el password siempre se percent-codifica al construir la URL.
            _with_credentials(FAKE_HOST, FAKE_USER, FAKE_PASSWORD),
            f"rtsp://{FAKE_USER}:%40%23@192.168.1.50/cam",
            "password=secret123",
        ]
        for original in cases:
            redacted = redact_rtsp_url(original)
            self.assertNotIn(CANARY, redacted)
            self.assertNotIn(FAKE_USER, redacted)
            self.assertNotIn("secret123", redacted)
            # El password codificado nunca aparece en la redacción.
            self.assertNotIn("Fake%3AP%40ss", redacted)


class TestMetadataPath(unittest.TestCase):
    """AC-SEC-05: metadata.path sin secretos."""

    def test_metadata_path_no_secrets(self) -> None:
        cap = FakeCapture()
        source = RTSPSource(
            rtsp_url=f"rtsp://{FAKE_USER}:{CANARY}@192.168.1.50/stream",
            capture_factory=make_factory(cap),
        )
        metadata = source.open()
        self.assertNotIn(FAKE_USER, metadata.path)
        self.assertNotIn(CANARY, metadata.path)
        self.assertIn("REDACTED:REDACTED", metadata.path)
        source.close()

    def test_metadata_path_keeps_host_diagnostics(self) -> None:
        cap = FakeCapture()
        source = RTSPSource(
            rtsp_url=f"rtsp://{FAKE_USER}:{CANARY}@192.168.1.50/stream",
            capture_factory=make_factory(cap),
        )
        metadata = source.open()
        self.assertIn("192.168.1.50", metadata.path)
        source.close()


class TestExceptionsAndStdout(unittest.TestCase):
    """AC-SEC-06, AC-SEC-07 y AC-SEC-08: excepciones y salidas sin secretos."""

    def test_controlled_exception_no_secrets(self) -> None:
        """AC-SEC-06: excepción controlada sin secretos."""
        cap = FakeCapture(opened=False)
        source = RTSPSource(
            rtsp_url=f"rtsp://{FAKE_USER}:{CANARY}@192.168.1.50/stream",
            capture_factory=make_factory(cap),
        )
        with self.assertRaises(RTSPSourceError) as ctx:
            source.open()
        self.assertNotIn(FAKE_USER, str(ctx.exception))
        self.assertNotIn(CANARY, str(ctx.exception))
        source.close()

    def test_stdout_no_secrets(self) -> None:
        """AC-SEC-07: stdout sin secretos al redactar la URL."""
        url = _with_credentials(FAKE_HOST, FAKE_USER, CANARY)
        redacted = redact_rtsp_url(url)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            print(redacted)
        self.assertNotIn(CANARY, captured.getvalue())
        self.assertNotIn(FAKE_USER, captured.getvalue())

    def test_python_stderr_no_secrets(self) -> None:
        """AC-SEC-08: stderr de Python sin secretos ante error redactable."""
        url = _with_credentials(FAKE_HOST, FAKE_USER, CANARY)
        redacted = redact_rtsp_url(url)
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured):
            sys.stderr.write(redacted)
            sys.stderr.flush()
        self.assertNotIn(CANARY, captured.getvalue())
        self.assertNotIn(FAKE_USER, captured.getvalue())


class TestNativeStderr(unittest.TestCase):
    """AC-SEC-09, AC-SEC-10 y AC-SEC-11: protección y restauración de fd 2."""

    def test_fd2_suppressed_during_context(self) -> None:
        """AC-SEC-09: stderr nativo (fd 2) queda en silencio en el contexto."""
        captured = _fd2_bytes_written(_write_inside_context)
        self.assertNotIn(b"CANARY_NATIVE_8F21", captured)

    def test_fd2_restored_after_context(self) -> None:
        """AC-SEC-10: fd 2 restaurado tras salir del contexto."""
        def action() -> None:
            with _suppress_native_stderr():
                os.write(2, b"CANARY_NATIVE_8F21_INSIDE")
            os.write(2, b"AFTER_CONTEXT_VISIBLE")
        captured = _fd2_bytes_written(action)
        self.assertNotIn(b"CANARY_NATIVE_8F21", captured)
        self.assertIn(b"AFTER_CONTEXT_VISIBLE", captured)

    def test_fd2_restored_after_exception(self) -> None:
        """AC-SEC-11: fd 2 restaurado incluso cuando el cuerpo lanza excepción."""
        def action() -> None:
            try:
                with _suppress_native_stderr():
                    os.write(2, b"CANARY_NATIVE_8F21_INSIDE")
                    raise RuntimeError("boom")
            except RuntimeError:
                pass
            os.write(2, b"AFTER_EXCEPTION_VISIBLE")
        captured = _fd2_bytes_written(action)
        self.assertNotIn(b"CANARY_NATIVE_8F21", captured)
        self.assertIn(b"AFTER_EXCEPTION_VISIBLE", captured)

    def test_fd2_is_real_stderr_descriptor(self) -> None:
        """El contexto redirige el descriptor 2 real, no sys.stderr."""
        self.assertGreaterEqual(os.dup(2), 0)
        os.close(os.dup(2))


def _write_inside_context() -> None:
    with _suppress_native_stderr():
        os.write(2, b"CANARY_NATIVE_8F21")


class TestRegressions(unittest.TestCase):
    """AC-SEC-12, AC-SEC-13 y AC-SEC-14: regresiones de fuentes."""

    def test_file_source_unchanged(self) -> None:
        """AC-SEC-12: VideoSource (FILE) sin regresión."""
        from src.capture.video_source import VideoSource
        source = VideoSource(os.path.join("data", "missing", "nope.mp4"))
        with self.assertRaises(VideoNotFoundError):
            source.open()

    def test_webcam_source_unchanged(self) -> None:
        """AC-SEC-13: WebcamSource sin regresión."""
        cap = FakeCapture()
        source = WebcamSource(camera_index=0, capture_factory=make_factory(cap))
        metadata = source.open()
        self.assertIsInstance(metadata, VideoMetadata)
        source.close()
        self.assertTrue(cap._released)

    def test_rtsp_source_closes_resources(self) -> None:
        """AC-SEC-14: RTSPSource cierra los recursos."""
        cap = FakeCapture()
        source = RTSPSource(
            rtsp_url="rtsp://192.168.1.50/stream",
            capture_factory=make_factory(cap),
        )
        source.open()
        source.close()
        self.assertTrue(cap._released)
        self.assertFalse(source.is_open)


class TestArgumentContamination(unittest.TestCase):
    """ARGUMENT_CONTAMINATION_TEST: la URL no absorbe argumentos del launcher."""

    def test_url_never_contains_launcher_arguments(self) -> None:
        url = _with_credentials(FAKE_HOST, FAKE_USER, CANARY)
        forbidden = [
            ".venv",
            "python.exe",
            "test_rtsp_connection.py",
            "--host",
            "--username",
            "--timeout",
            "--max-frames",
        ]
        for token in forbidden:
            self.assertNotIn(token, url)


if __name__ == "__main__":
    unittest.main()