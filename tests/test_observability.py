"""Pruebas unitarias para src.observability (logging + redacción)."""

import logging
import tempfile
import unittest
from pathlib import Path

from src.observability.logging_setup import (
    new_run_id,
    redact_rtsp_url,
    setup_logging,
)


def _close_log_handlers() -> None:
    """Cierra y elimina los handlers del logger para liberar archivos."""
    logger = logging.getLogger("tukevision")
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


class TestLoggingSetup(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        _close_log_handlers()
        self.tmp.cleanup()

    def test_new_run_id_formato(self) -> None:
        """El RUN_ID tiene el formato RUN-XXXXXX."""
        run_id = new_run_id()
        self.assertRegex(run_id, r"^RUN-[0-9A-F]{6}$")

    def test_redact_rtsp_url_oculta_credenciales(self) -> None:
        """Las credenciales de una URL RTSP nunca quedan en el texto."""
        url = "rtsp://admin:secreto123@192.168.1.50:554/stream"
        redacted = redact_rtsp_url(url)
        self.assertNotIn("admin", redacted)
        self.assertNotIn("secreto123", redacted)
        self.assertIn("REDACTED", redacted)
        self.assertIn("192.168.1.50", redacted)

    def test_redact_rtsp_url_sin_credenciales_no_cambia(self) -> None:
        """URL sin credenciales se conserva intacta."""
        url = "rtsp://192.168.1.50:554/stream"
        self.assertEqual(redact_rtsp_url(url), url)

    def test_redact_password_plain(self) -> None:
        """Se redacta la etiqueta password en texto plano."""
        text = "password=muy-secreto"
        self.assertNotIn("muy-secreto", redact_rtsp_url(text))

    def test_redact_rtsp_url_none(self) -> None:
        """Valores nulos se toleran."""
        self.assertEqual(redact_rtsp_url(""), "")
        self.assertIsNone(redact_rtsp_url(None))

    def test_setup_logging_crea_archivo(self) -> None:
        """setup_logging crea un archivo de log en logs/."""
        logger = setup_logging(
            log_dir=self.tmp.name,
            run_id="RUN-ABC123",
            level=logging.DEBUG,
        )
        log_file = Path(self.tmp.name) / "tukevision-RUN-ABC123.log"
        self.assertTrue(log_file.exists())
        self.assertEqual(logger.name, "tukevision")

    def test_setup_logging_es_idempotente(self) -> None:
        """Llamadas repetidas no duplican handlers RotatingFileHandler."""
        setup_logging(log_dir=self.tmp.name, run_id="RUN-AAA111")
        logger = setup_logging(log_dir=self.tmp.name, run_id="RUN-BBB222")
        handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        self.assertEqual(len(handlers), 1)


class TestLoggingRedactionEndToEnd(unittest.TestCase):
    """El contenido del archivo de log no contiene credenciales."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        _close_log_handlers()
        self.tmp.cleanup()

    def test_log_no_contiene_credenciales(self) -> None:
        logger = setup_logging(
            log_dir=self.tmp.name,
            run_id="RUN-RED01",
            level=logging.INFO,
        )
        secret = "sup3r-s3cret"
        logger.info(
            "Conectando a rtsp://usuario:%s@192.168.1.50:554/stream",
            secret,
        )
        for handler in logger.handlers:
            handler.flush()
        content = (Path(self.tmp.name) / "tukevision-RUN-RED01.log").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(secret, content)
        self.assertNotIn("usuario", content)
        self.assertIn("REDACTED", content)


if __name__ == "__main__":
    unittest.main()
