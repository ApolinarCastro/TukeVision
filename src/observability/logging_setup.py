"""Configuración de logging para la operación local.

Responsabilidad única: preparar el logging a archivo de la ejecución
local usando la biblioteca estándar (`logging`), con un RUN_ID por
ejecución, rotación por tamaño y redacción de credenciales. No agrega
capacidades al núcleo: solo registra lo que ya ocurre.

Principio de privacidad (LOOP-0001): las credenciales (p. ej. URL RTSP
con usuario y contraseña) nunca se guardan, persisten, loguean ni
muestran. Todo mensaje que pase por los handlers es redactado.
"""

import logging
import re
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

# rtsp://user:pass@host/path  ->  rtsp://REDACTED:REDACTED@host/path
_RTSP_URL_PATTERN = re.compile(
    r"(rtsp://)([^/@:\s]+)(?::([^/@:\s]+))?@",
    re.IGNORECASE,
)
_CREDENTIAL_PATTERN = re.compile(
    r"(password\s*[:=]\s*)\S+", re.IGNORECASE
)


def redact_rtsp_url(text: str) -> str:
    """Redacta credenciales embebidas en una URL RTSP."""
    if not text:
        return text

    def _replace(match: re.Match) -> str:
        return f"{match.group(1)}REDACTED:REDACTED@"

    redacted = _RTSP_URL_PATTERN.sub(_replace, text)
    redacted = _CREDENTIAL_PATTERN.sub(r"\1REDACTED", redacted)
    return redacted


class RedactingFormatter(logging.Formatter):
    """Formatter que redacta credenciales en cada registro."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return redact_rtsp_url(message)


def new_run_id() -> str:
    """Genera un identificador único para una ejecución local."""
    short = uuid.uuid4().hex[:6].upper()
    return f"RUN-{short}"


def setup_logging(
    log_dir: str = "logs",
    run_id: Optional[str] = None,
    level: int = logging.INFO,
    max_bytes: int = 1_000_000,
    backup_count: int = 2,
) -> logging.Logger:
    """Configura el logging a archivo con rotación.

    Devuelve el logger raíz de TukeVision. Es idempotente: si ya fue
    configurado, se devuelve el logger existente sin duplicar handlers.
    """
    run_id = run_id or new_run_id()
    logger = logging.getLogger("tukevision")
    if any(
        isinstance(h, RotatingFileHandler)
        for h in logger.handlers
    ):
        logger.setLevel(level)
        for h in list(logger.handlers):
            if isinstance(h, RotatingFileHandler):
                h.close()
                logger.removeHandler(h)
            elif isinstance(h, logging.StreamHandler):
                logger.removeHandler(h)
        logger.handlers.clear()

    logger.setLevel(level)
    logger.propagate = False

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / f"tukevision-{run_id}.log"

    handler = RotatingFileHandler(
        str(log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(RedactingFormatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(handler)

    stream = logging.StreamHandler()
    stream.setFormatter(RedactingFormatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(stream)

    logger.info("Logging iniciado. RUN_ID=%s", run_id)
    return logger
