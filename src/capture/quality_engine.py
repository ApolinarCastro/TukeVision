"""Video Quality Engine para TukeVision (recovered from portable LOOP-0017B).

Responsabilidad única: decidir qué stream RTSP usar según el contexto
(multiview vs focus) y la evidencia física de estabilidad por cámara.

NO inventa resolución. NO hace upscaling. NO modifica frames.
Solo selecciona subtype=0 (main) o subtype=1 (sub) basado en perfil
y fallback controlado.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class QualityProfile(Enum):
    """Perfiles de calidad de video."""
    ECONOMY = "economy"      # Thumbnails / multiview → substream (subtype=1)
    QUALITY = "quality"      # Cámara enfocada / grande → main stream (subtype=0) si estable
    AUTO = "auto"            # Adaptativo: multiview→ECO, focus→QUALITY con fallback


class StreamType(Enum):
    """Tipo de stream RTSP."""
    MAIN = 0      # subtype=0 - Alta calidad
    SUB = 1       # subtype=1 - Ligero


@dataclass(frozen=True)
class CameraStreamCapability:
    """Capacidad de stream medida físicamente para una cámara."""
    camera_id: int
    main_resolution: Optional[str]      # ej: "640x360"
    main_fps: Optional[float]
    main_stable: bool                   # YOLO + Track funcionando
    sub_resolution: Optional[str]       # ej: "352x240"
    sub_fps: Optional[float]
    sub_stable: bool                    # YOLO + Track funcionando
    last_tested: str                    # ISO timestamp


class VideoQualityEngine:
    """
    Motor de decisión de calidad de video.

    Usa evidencia física (capabilities) para elegir el mejor stream
    según el perfil solicitado y el contexto de uso.
    """

    def __init__(self) -> None:
        self._capabilities: Dict[int, CameraStreamCapability] = {}
        self._profile = QualityProfile.AUTO
        self._focus_camera_id: Optional[int] = None

    def register_capability(self, capability: CameraStreamCapability) -> None:
        """Registra la capacidad medida de una cámara."""
        self._capabilities[capability.camera_id] = capability

    def get_capability(self, camera_id: int) -> Optional[CameraStreamCapability]:
        """Obtiene la capacidad registrada de una cámara."""
        return self._capabilities.get(camera_id)

    def set_profile(self, profile: QualityProfile) -> None:
        """Establece el perfil de calidad global."""
        self._profile = profile

    def set_focus_camera(self, camera_id: Optional[int]) -> None:
        """Establece la cámara en foco (vista grande)."""
        self._focus_camera_id = camera_id

    def get_stream_type(self, camera_id: int, is_focus: bool = False) -> StreamType:
        """
        Decide qué stream usar para una cámara.

        Args:
            camera_id: ID de la cámara (1-16)
            is_focus: True si la cámara está en modo FOCUS (vista grande)

        Returns:
            StreamType.MAIN (0) o StreamType.SUB (1)
        """
        cap = self._capabilities.get(camera_id)

        # Sin datos → default seguro: substream
        if cap is None:
            return StreamType.SUB

        # Perfil ECONOMY: siempre substream
        if self._profile == QualityProfile.ECONOMY:
            return StreamType.SUB

        # Perfil QUALITY: main si está disponible y estable
        if self._profile == QualityProfile.QUALITY:
            if cap.main_stable and cap.main_resolution:
                return StreamType.MAIN
            return StreamType.SUB

        # Perfil AUTO (default)
        if is_focus or camera_id == self._focus_camera_id:
            # Modo FOCUS: intentar main stream
            if cap.main_stable and cap.main_resolution:
                return StreamType.MAIN
            # Fallback a substream
            return StreamType.SUB
        else:
            # Modo MULTIVIEW/THUMBNAIL: substream
            return StreamType.SUB

    def get_subtype(self, camera_id: int, is_focus: bool = False) -> int:
        """Devuelve el valor numérico de subtype (0 o 1)."""
        return self.get_stream_type(camera_id, is_focus).value

    def get_fallback_subtype(self, camera_id: int, failed_subtype: int) -> Optional[int]:
        """
        Devuelve el subtype alternativo si el actual falla.

        Args:
            camera_id: ID de la cámara
            failed_subtype: El subtype que falló (0 o 1)

        Returns:
            Subtype alternativo o None si no hay fallback
        """
        cap = self._capabilities.get(camera_id)
        if cap is None:
            return None

        if failed_subtype == 0:  # Main falló → probar sub
            if cap.sub_stable and cap.sub_resolution:
                return 1
        else:  # Sub falló → probar main (solo si hay evidencia de estabilidad)
            if cap.main_stable and cap.main_resolution:
                return 0
        return None


# Instancia global (singleton pattern simple)
_quality_engine: Optional[VideoQualityEngine] = None


def get_quality_engine() -> VideoQualityEngine:
    """Obtiene la instancia global del motor de calidad.

    NO registra capacidades auditadas hardcoded (OC-01): la auditoría
    física de cámaras es específica de cada despliegue y debe registrarse
    desde el catálogo config-driven (src.domain.catalog) o runtime. Sin
    capacidades el motor decide de forma segura por defecto substream.
    """
    global _quality_engine
    if _quality_engine is None:
        _quality_engine = VideoQualityEngine()
    return _quality_engine


def reset_quality_engine() -> None:
    """Limpia la instancia global (útil en tests y reloads)."""
    global _quality_engine
    _quality_engine = None


def register_capability(camera_id: int, capability: CameraStreamCapability) -> None:
    """Registra una capacidad medida en el motor global (config-driven)."""
    get_quality_engine().register_capability(camera_id, capability)