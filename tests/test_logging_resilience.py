"""Logging resilience tests (MACRO-OC-02, Bloque J).

The operator observed repeated ``--- Logging error ---`` in the console. Root
cause class: the capture layer redirects the native stderr descriptor (fd 2)
to silence OpenCV; a plain ``logging.StreamHandler`` then fails to
write/flush (OSError WinError 1) and logging prints ``--- Logging error ---``
on every record. The fix keeps the file sink authoritative and makes the
console echo best-effort: ``_ResilientStreamHandler`` drops the echo only when
the descriptor is unusable, without suppressing the file log or other errors.
"""

import io
import logging
import sys
import tempfile
import unittest
from pathlib import Path

from src.observability.logging_setup import (
    _ResilientStreamHandler,
    setup_logging,
    redact_rtsp_url,
)


class _BrokenStream:
    """Mimics stderr whose underlying fd was closed/redirected (OSError)."""

    def write(self, _text):
        raise OSError(9, "Bad file descriptor")

    def flush(self):
        raise OSError(9, "Bad file descriptor")

    @property
    def closed(self):
        return False


class TestResilientStreamHandler(unittest.TestCase):
    def tearDown(self):
        logging.raiseExceptions = True

    def test_resilient_handler_suppresses_broken_stderr_errors(self):
        captured = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured
        try:
            log = logging.getLogger("tukevision.test_broken")
            log.handlers = []
            log.propagate = False
            log.setLevel(logging.INFO)
            log.addHandler(_ResilientStreamHandler(_BrokenStream()))
            good_sink = io.StringIO()
            log.addHandler(logging.StreamHandler(good_sink))
            logging.raiseExceptions = True
            log.info("mensaje de prueba")
            self.assertIn("mensaje de prueba", good_sink.getvalue())
        finally:
            sys.stderr = old_stderr
        self.assertNotIn("Logging error", captured.getvalue())

    def test_plain_stream_handler_would_emit_logging_error(self):
        # Control: proves the failure mode exists and the fix is meaningful.
        captured = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured
        try:
            log = logging.getLogger("tukevision.test_plain_broken")
            log.handlers = []
            log.propagate = False
            log.setLevel(logging.INFO)
            log.addHandler(logging.StreamHandler(_BrokenStream()))
            logging.raiseExceptions = True
            log.info("boom")
        finally:
            sys.stderr = old_stderr
        self.assertIn("Logging error", captured.getvalue())


class TestSetupLogging(unittest.TestCase):
    def test_setup_logging_writes_to_file_and_console_echo(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = setup_logging(
                log_dir=str(Path(tmp) / "logs"),
                run_id="RUN-TEST",
                level=logging.INFO,
            )
            try:
                logger.info("hola desde el test")
                logs = list((Path(tmp) / "logs").glob("tukevision-RUN-TEST.log"))
                self.assertEqual(len(logs), 1)
                content = logs[0].read_text(encoding="utf-8")
                self.assertIn("hola desde el test", content)
                # The logger uses the resilient stream handler (no plain one).
                self.assertTrue(
                    any(isinstance(h, _ResilientStreamHandler) for h in logger.handlers)
                )
            finally:
                for handler in list(logger.handlers):
                    handler.close()
                    logger.removeHandler(handler)

    def test_redaction_still_active(self):
        text = "rtsp://admin:clave@192.168.0.5/cam/realmonitor"
        self.assertNotIn("clave", redact_rtsp_url(text))
        self.assertIn("REDACTED", redact_rtsp_url(text))


if __name__ == "__main__":
    unittest.main()