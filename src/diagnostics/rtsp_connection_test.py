"""Diagnóstico de conexión RTSP autorizada.

Responsabilidad única: validar una URL RTSP proporcionada explícitamente
por un operador autorizado y devolver un resultado estructurado inmutable.

NO hace:
- descubrimiento de streams ni de dispositivos;
- construcción automática de credenciales;
- escaneo de red ni puertos;
- ejecución de YOLO, ByteTrack, observaciones, eventos, riesgo, alertas
  ni evidencia.

Reutiliza `RTSPSource` existente. Las credenciales solo existen en la URL
recibida y en la captura de OpenCV durante la ejecución; nunca se
persisten ni se incluyen en el resultado.

Etapas separadas del diagnóstico (un fallo se localiza en una etapa):
    NETWORK CONNECTIVITY -> RTSP OPEN -> AUTHENTICATION -> VIDEO FRAMES
La clasificación es prudente: si el backend no permite distinguir
autenticación de otro fallo de apertura, se reporta `STREAM_OPEN_FAILED`
(no se inventa una causa raíz).
"""

import time
from dataclasses import dataclass, replace
from typing import Callable, Optional, Tuple

import cv2

from src.capture.live_sources import RTSPSource
from src.capture.video_source import VideoSourceError
from src.observability.logging_setup import redact_rtsp_url


class RTSPNetworkState:
    """Estados de conectividad de red."""
    NETWORK_UNKNOWN = "NETWORK_UNKNOWN"
    NETWORK_REACHABLE = "NETWORK_REACHABLE"


class RTSPOpenState:
    """Estados de apertura del stream RTSP."""
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    STREAM_OPENED = "STREAM_OPENED"
    STREAM_OPEN_FAILED = "STREAM_OPEN_FAILED"


class RTSPFrameState:
    """Estados de recepción de fotogramas."""
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    NO_FRAMES = "NO_FRAMES"
    FRAMES_RECEIVED = "FRAMES_RECEIVED"
    TIMEOUT = "TIMEOUT"


class RTSPSourceState:
    """Estados de cierre de la fuente."""
    NOT_CLOSED = "NOT_CLOSED"
    SOURCE_CLOSED = "SOURCE_CLOSED"


@dataclass(frozen=True)
class RTSPDiagnosticResult:
    """Resultado inmutable del diagnóstico RTSP.

    Nunca contiene password ni la URL original con credenciales.
    """
    network_status: str = RTSPNetworkState.NETWORK_UNKNOWN
    stream_open_status: str = RTSPOpenState.NOT_ATTEMPTED
    frame_status: str = RTSPFrameState.NOT_ATTEMPTED
    frames_received: int = 0
    resolution: str = ""
    measured_fps: float = 0.0
    elapsed_seconds: float = 0.0
    error_category: str = "NONE"
    safe_message: str = ""
    source_closed: str = RTSPSourceState.NOT_CLOSED


def _measured_fps(frames_received: int, elapsed: float) -> float:
    if frames_received <= 0 or elapsed <= 0:
        return 0.0
    return frames_received / elapsed


class RTSPConnectionTest:
    """Ejecuta la prueba de conexión RTSP con límites determinísticos.

    Configuración de límites:
        connect_timeout_seconds: límite total de la etapa de apertura.
        test_duration_seconds: límite total de la prueba (apertura +
            lectura de fotogramas).
        max_frames: límite de fotogramas a leer.
    """

    def __init__(
        self,
        connect_timeout_seconds: float = 10.0,
        test_duration_seconds: float = 15.0,
        max_frames: int = 30,
        source_factory: Optional[Callable[[str], RTSPSource]] = None,
    ) -> None:
        self._connect_timeout_seconds = max(0.0, float(connect_timeout_seconds))
        self._test_duration_seconds = max(
            self._connect_timeout_seconds, float(test_duration_seconds)
        )
        self._max_frames = max(1, int(max_frames))
        self._source_factory = source_factory or (
            lambda url: RTSPSource(rtsp_url=url)
        )

    def _build_result(
        self,
        network_status: str = RTSPNetworkState.NETWORK_UNKNOWN,
        stream_open_status: str = RTSPOpenState.NOT_ATTEMPTED,
        frame_status: str = RTSPFrameState.NOT_ATTEMPTED,
        frames_received: int = 0,
        resolution: str = "",
        measured_fps: float = 0.0,
        elapsed_seconds: float = 0.0,
        error_category: str = "NONE",
        safe_message: str = "",
        source_closed: str = RTSPSourceState.NOT_CLOSED,
    ) -> RTSPDiagnosticResult:
        return RTSPDiagnosticResult(
            network_status=network_status,
            stream_open_status=stream_open_status,
            frame_status=frame_status,
            frames_received=frames_received,
            resolution=resolution,
            measured_fps=measured_fps,
            elapsed_seconds=elapsed_seconds,
            error_category=error_category,
            safe_message=safe_message,
            source_closed=source_closed,
        )

    def run(self, rtsp_url: str) -> RTSPDiagnosticResult:
        """Ejecuta el diagnóstico y devuelve un resultado inmutable.

        La URL solo se usa para abrir la fuente. No se persiste, no se
        registra con credenciales y no forma parte del resultado.
        """
        start = time.monotonic()
        source = self._source_factory(rtsp_url)
        source_closed = RTSPSourceState.NOT_CLOSED
        stream_open_status = RTSPOpenState.NOT_ATTEMPTED
        frame_status = RTSPFrameState.NOT_ATTEMPTED
        frames_received = 0
        resolution = ""
        error_category = "NONE"
        safe_message = ""
        network_status = RTSPNetworkState.NETWORK_UNKNOWN

        try:
            metadata = source.open()
            network_status = RTSPNetworkState.NETWORK_REACHABLE
            stream_open_status = RTSPOpenState.STREAM_OPENED
            if metadata.width and metadata.height:
                resolution = f"{metadata.width}x{metadata.height}"
            elif metadata.fps > 0:
                resolution = "desconocida"

            # Limitar la lectura de fotogramas de forma determinística.
            for _ in range(self._max_frames):
                elapsed = time.monotonic() - start
                if elapsed >= self._test_duration_seconds:
                    frame_status = RTSPFrameState.TIMEOUT
                    safe_message = (
                        f"Límite de duración alcanzado tras {elapsed:.1f}s"
                    )
                    break
                result = source.read()
                if result is None:
                    if frames_received == 0:
                        frame_status = RTSPFrameState.NO_FRAMES
                        safe_message = (
                            "La fuente se abrió pero no entregó fotogramas"
                        )
                    else:
                        frame_status = RTSPFrameState.FRAMES_RECEIVED
                    break
                _index, frame = result
                if frame is not None and frame.size > 0:
                    frames_received += 1

            if frame_status == RTSPFrameState.NOT_ATTEMPTED:
                frame_status = RTSPFrameState.FRAMES_RECEIVED

            elapsed = time.monotonic() - start
            result = self._build_result(
                network_status=network_status,
                stream_open_status=stream_open_status,
                frame_status=frame_status,
                frames_received=frames_received,
                resolution=resolution,
                measured_fps=_measured_fps(frames_received, elapsed),
                elapsed_seconds=round(elapsed, 3),
                error_category=error_category,
                safe_message=safe_message,
                source_closed=RTSPSourceState.NOT_CLOSED,
            )
            return self._finish(result, source, start)

        except VideoSourceError as e:
            elapsed = time.monotonic() - start
            network_status = RTSPNetworkState.NETWORK_UNKNOWN
            stream_open_status = RTSPOpenState.STREAM_OPEN_FAILED
            # Clasificación prudente: no afirmamos AUTHENTICATION_FAILED
            # si el backend no permite distinguirlo.
            error_category = "UNKNOWN_CONNECTION_FAILURE"
            safe_message = "No se pudo abrir la fuente RTSP"
            result = self._build_result(
                network_status=network_status,
                stream_open_status=stream_open_status,
                frame_status=RTSPFrameState.NOT_ATTEMPTED,
                elapsed_seconds=round(elapsed, 3),
                error_category=error_category,
                safe_message=safe_message,
                source_closed=RTSPSourceState.NOT_CLOSED,
            )
            return self._finish(result, source, start)
        except Exception as e:  # noqa: BLE001
            elapsed = time.monotonic() - start
            stream_open_status = RTSPOpenState.STREAM_OPEN_FAILED
            error_category = "UNKNOWN_CONNECTION_FAILURE"
            safe_message = "Fallo no clasificado al validar la fuente RTSP"
            result = self._build_result(
                network_status=network_status,
                stream_open_status=stream_open_status,
                frame_status=RTSPFrameState.NOT_ATTEMPTED,
                elapsed_seconds=round(elapsed, 3),
                error_category=error_category,
                safe_message=safe_message,
                source_closed=RTSPSourceState.NOT_CLOSED,
            )
            return self._finish(result, source, start)

    def _finish(self, result: RTSPDiagnosticResult, source, start: float) -> RTSPDiagnosticResult:
        """Cierra la fuente y devuelve el resultado con el cierre real."""
        try:
            source.close()
            closed = RTSPSourceState.SOURCE_CLOSED
        except Exception:  # noqa: BLE001
            closed = RTSPSourceState.NOT_CLOSED
        return replace(result, source_closed=closed)


def summarize_result(result: RTSPDiagnosticResult) -> str:
    """Devuelve un texto seguro (sin credenciales) del resultado."""
    lines = [
        f"NETWORK_STATUS: {result.network_status}",
        f"STREAM_OPEN_STATUS: {result.stream_open_status}",
        f"FRAME_STATUS: {result.frame_status}",
        f"FRAMES_RECEIVED: {result.frames_received}",
        f"RESOLUTION: {result.resolution or '-'}",
        f"MEASURED_FPS: {result.measured_fps:.2f}",
        f"ELAPSED_SECONDS: {result.elapsed_seconds:.2f}",
        f"ERROR_CATEGORY: {result.error_category}",
        f"SOURCE_CLOSED: {result.source_closed}",
    ]
    if result.safe_message:
        lines.append(f"MESSAGE: {result.safe_message}")
    return "\n".join(lines)


def build_safe_display(rtsp_url: str) -> str:
    """Representación segura de la URL para mostrar o registrar."""
    return redact_rtsp_url(rtsp_url)
