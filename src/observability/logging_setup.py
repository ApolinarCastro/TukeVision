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


class _ResilientStreamHandler(logging.StreamHandler):
    """StreamHandler que no rompe el logging cuando stderr es inutilizable.

    El sink primario es el archivo; el eco a consola es best-effort. La capa
    de captura (live_sources) redirige temporalmente el descriptor nativo de
    stderr (fd 2) para silenciar OpenCV; en esos estados un `StreamHandler`
    estándar falla al escribir/flushear (OSError WinError 1) y `logging`
    emite los repetidos ``--- Logging error ---``. Este handler omite solo el
    eco a consola cuando el descriptor está cerrado/redirigido sin ocultar
    nada en el log a archivo.
    """

    def emit(self, record: logging.LogRecord) -> None:
        if self.stream is None:
            return
        try:
            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.flush()
        except (OSError, ValueError):
            # stderr cerrado/redirigido (captura de OpenCV): el archivo es
            # el sink autoritativo; se omite solo el eco a consola.
            pass
        except Exception:
            # Errores reales (formato, etc.) sí se reportan.
            self.handleError(record)


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

    stream = _ResilientStreamHandler()
    stream.setFormatter(RedactingFormatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(stream)

    logger.info("Logging iniciado. RUN_ID=%s", run_id)
    return logger


def atomic_write_text(target: str | Path, content: str, encoding: str = "utf-8", retries: int = 5) -> Path:
    """Atomic file write with unique temporary file and bounded retry for Windows locks.
    
    Prevents PermissionError [WinError 5] when temporary files or destinations are briefly
    held open by antivirus, indexers, or asynchronous telemetry readers.
    """
    import os
    import tempfile
    import time
    
    target_path = Path(target).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create unique temp file in the same directory (required for atomic rename)
    fd, tmp_file = tempfile.mkstemp(prefix=f".{target_path.name}.", suffix=".tmp", dir=target_path.parent)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
            
        last_exc = None
        for attempt in range(retries):
            try:
                os.replace(tmp_file, target_path)
                return target_path
            except (PermissionError, OSError) as exc:
                last_exc = exc
                time.sleep(0.02 * (2 ** attempt))  # 20ms, 40ms, 80ms, 160ms, 320ms
        if last_exc:
            raise last_exc
        return target_path
    finally:
        try:
            if os.path.exists(tmp_file):
                os.unlink(tmp_file)
        except OSError:
            pass
