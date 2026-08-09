"""Estado de la interfaz operativa local.

Responsabilidad única: modelar el estado de la UI (fuente, estado de
ejecución, seguimiento, riesgo real, alertas y evidencia) sin autoridad
de negocio. No decide ni calcula: solo conserva datos ya producidos por
el pipeline.
"""

from typing import List, Optional, Tuple


class AppStatus:
    """Estados de ejecución de la interfaz."""
    READY = "READY"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class UiState:
    """Estado mutable de la interfaz, actualizado por el controlador.

    Este estado es de presentación. El riesgo que muestra proviene del
    pipeline (risk_text / alertas reales); nunca se calcula aquí.
    """

    def __init__(self) -> None:
        self.status: str = AppStatus.READY
        self.source_kind: str = "FILE"
        self.source_type: str = ""
        self.source_state: str = ""
        self.resolution: str = ""
        self.fps: float = 0.0
        self.source_path_display: str = ""
        self.zone_id: str = ""
        self.zone_name: str = ""
        self.followed_track: Optional[int] = None
        self.permanence_seconds: float = 0.0
        self.risk_text: str = ""
        self.latest_risk_score: Optional[int] = None
        self.alert_log: List[dict] = []
        self.evidence_paths: List[str] = []
        self.frames_processed: int = 0
        self.persons_detected: int = 0
        self.error: str = ""
        self.final_status: str = ""

    def reset_run(self) -> None:
        """Reinicia campos de una ejecución (no la configuración)."""
        self.source_type = ""
        self.source_state = ""
        self.resolution = ""
        self.fps = 0.0
        self.followed_track = None
        self.permanence_seconds = 0.0
        self.risk_text = ""
        self.latest_risk_score = None
        self.alert_log = []
        self.evidence_paths = []
        self.frames_processed = 0
        self.persons_detected = 0
        self.error = ""
        self.final_status = ""


def followed_track_id(snapshot) -> Optional[int]:
    """Selecciona la persona a destacar en el panel.

    Prioriza las personas dentro de la zona y, entre ellas, la de mayor
    permanencia; si ninguna está en la zona, la de mayor permanencia.
    """
    in_zone = [
        t for t in snapshot.tracked_objects
        if t.track_id in snapshot.in_zone_track_ids
    ]
    pool = in_zone or list(snapshot.tracked_objects)
    if not pool:
        return None
    return max(
        pool, key=lambda o: snapshot.stays_seconds.get(o.track_id, 0.0)
    ).track_id


def redact_source_display(source_kind: str, snapshot) -> str:
    """Texto de fuente a mostrar en pantalla.

    Para RTSP nunca se muestra la URL ni credenciales: se muestra el
    texto redactado.
    """
    if source_kind == "RTSP":
        return "RTSP: REDACTED"
    return f"{snapshot.source_type}  {snapshot.source_path}"
