"""Vista Tkinter de la interfaz operativa local.

Responsabilidad única: presentar widgets y actualizarlos desde el hilo
principal (vía Tk.after()). Nunca modifica widgets desde el hilo de
trabajo. Convierte los frames del pipeline a PhotoImage usando PIL/OpenCV,
sin introducir dependencias nuevas.

Recuperación visual quirúrgica (LOOP-0019B): se reutilizan los patrones
probados del Command Center portable (LOOP-0017B, preservado en
archive/legacy/portable_migrate_0018u):

  - Paneles de video dinámicos sobre Canvas: llenan el espacio disponible
    y nunca quedan limitados a un tamaño fijo artificial.
  - fit_display_size: preserva la relación de aspecto, escala SOLO la copia
    de presentación con LANCZOS (nunca se toca el frame analítico).
  - bgr_frame_to_rgb: punto único de conversión de color.
  - Overlays legibles sin tapar la escena; información técnica secundaria
    movida al panel lateral.

Expansión OC-01 / OC-05 / OC-06 / OC-07 (integración MACRO-OC-01):

  - El grid es config-driven: 1 -> 4 -> 16 -> N (sin supuestos de 4 cámaras).
  - Modo FOCUS por doble clic / clic (navegación de operador), back-to-grid,
    next/previous y fullscreen.
  - Selector de tienda y cámara derivados del catálogo multitienda.
  - Digital zoom sobre el frame ya existente (nunca PTZ físico).
  - PTZ físico se expone SOLO cuando la cámara lo declara (ptz_capability).

El frame de procesamiento nunca se modifica aquí; la presentación es una
vista que NO reescribe el pipeline, RTSP, YOLO ni tracking.
"""

import io
import os
from pathlib import Path
import time
from tkinter import filedialog, messagebox, ttk
from typing import Optional
import tkinter as tk

import cv2
from PIL import Image

from src.capture.rtsp_url import build_rtsp_url
from src.ui.state import AppStatus
from src.ui.grid_layout import (
    cycle_grid_preset,
    grid_layout,
    grid_cells,
    grid_capacity,
    EMPTY_SLOT_LABEL,
)
from src.localization.i18n import I18n, _
from src.ui.design_tokens import DesignTokens
from src.ui.tk_operational_panels import (
    OperationalCommandCenterModes,
    OperationalPanelsController,
)


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "multistore.active.json"


# ---------------------------------------------------------------------------
# Design System (recuperado del Command Center portable, LOOP-0017B)
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#0F172A",
    "panel": "#192134",
    "panel_muted": "#10192E",
    "border": "#2E3D5E",
    "text": "#E6E8EE",
    "text_dim": "#94A3B8",
    "accent": "#38BDF8",
    "accent_dim": "#1B3A5A",
    "online": "#22C55E",
    "degraded": "#F59E0B",
    "alert": "#EF4444",
    "offline": "#64748B",
    "focus": "#7C3AED",
}

FONT_TITLE = ("Segoe UI", 15, "bold")
FONT_SUBTITLE = ("Segoe UI", 8)
FONT_PANEL_TITLE = ("Segoe UI", 9, "bold")
FONT_BODY = ("Segoe UI", 9)
FONT_BODY_BOLD = ("Segoe UI", 9, "bold")
FONT_SMALL = ("Segoe UI", 8)

# Digital zoom bounds (BLOCK F): zoom acts on the presented image only.
MIN_ZOOM = 1.0
MAX_ZOOM = 4.0
ZOOM_STEP = 0.5
ZOOM_TOGGLE = 2.0


def multicamera_control_state(status: str) -> dict:
    return {"show_legacy": False, "stop_enabled": status == AppStatus.RUNNING}


def fit_display_size(
    src_w: int, src_h: int, max_w: int, max_h: int, *, allow_upscale: bool = False
):
    """Tamaño de presentación que llena el área máxima sin deformar.

    Conserva la relación de aspecto. En GRID nunca escala por encima de la
    resolución de la fuente (sin fake upscale). En FOCUS (``allow_upscale``)
    la vista expandida puede escalar proporcionalmente hasta llenar el área
    disponible entre header y barra de controles, preservando el aspecto
    (letterbox/pillarbox) y sin estirar el video (DEF-UI-FOCUS-SIZE-02).
    """
    if src_w <= 0 or src_h <= 0 or max_w <= 0 or max_h <= 0:
        return int(src_w), int(src_h)
    if allow_upscale:
        scale = min(max_w / src_w, max_h / src_h)
        # Rule 28: No agresivo upscale para fuentes SD (ej. 352x240)
        if src_w < 720:
            scale = min(1.0, scale) # Preferir presentación letterbox nativa
    else:
        scale = min(1.0, max_w / src_w, max_h / src_h)
    disp_w = max(1, int(round(src_w * scale)))
    disp_h = max(1, int(round(src_h * scale)))
    return disp_w, disp_h


def bgr_frame_to_rgb(frame):
    """Convierte BGR (OpenCV) a RGB. Único punto de conversión de color."""
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def build_display_image(frame, max_w: int, max_h: int, *, allow_upscale: bool = False):
    """Construye la imagen de presentación sin modificar el frame original.

    BGR -> RGB -> escala LANCZOS (solo presentación; upscale solo si el modo
    FOCUS lo permite explícitamente). El frame de entrada no se modifica: el
    pipeline sigue recibiendo el frame real. Reutiliza el patrón probado del
    portable (LOOP-0017B).
    """
    src_h, src_w = frame.shape[:2]
    disp_w, disp_h = fit_display_size(
        src_w, src_h, max_w, max_h, allow_upscale=allow_upscale
    )
    rgb = bgr_frame_to_rgb(frame)
    image = Image.fromarray(rgb)
    if (disp_w, disp_h) != (src_w, src_h):
        image = image.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
    return image


def build_zoomed_display_image(
    frame, max_w: int, max_h: int, zoom_factor: float, *, allow_upscale: bool = False
):
    """Digital zoom over the existing frame (OC-07) — centered variant."""
    return build_viewport_display_image(
        frame, max_w, max_h, zoom_factor, pan_x=0, pan_y=0, allow_upscale=allow_upscale
    )


def _clamp_pan(pan_x: float, pan_y: float, src_w: int, src_h: int, crop_w: int, crop_h: int):
    max_x = max(0, (src_w - crop_w) / 2)
    max_y = max(0, (src_h - crop_h) / 2)
    return max(-max_x, min(max_x, float(pan_x))), max(-max_y, min(max_y, float(pan_y)))


def build_viewport_display_image(
    frame, max_w: int, max_h: int, zoom_factor: float, pan_x: float = 0, pan_y: float = 0, *, allow_upscale: bool = False
):
    """Viewport with scale + pan (BLOCK F/G/H).

    Draw overlays in source frame -> crop viewport -> resize for presentation.
    Pan is offset from center in source pixels, clamped to valid frame.
    Scale >=1.0. When scale==1.0 pan is ignored.
    """
    src_h, src_w = frame.shape[:2]
    factor = max(1.0, float(zoom_factor))
    crop_w = max(1, int(round(src_w / factor)))
    crop_h = max(1, int(round(src_h / factor)))
    if factor == 1.0:
        pan_x = 0
        pan_y = 0
    else:
        pan_x, pan_y = _clamp_pan(pan_x, pan_y, src_w, src_h, crop_w, crop_h)
    cx = src_w / 2 + pan_x
    cy = src_h / 2 + pan_y
    x0 = int(round(cx - crop_w / 2))
    y0 = int(round(cy - crop_h / 2))
    x0 = max(0, min(src_w - crop_w, x0))
    y0 = max(0, min(src_h - crop_h, y0))
    region = frame[y0:y0 + crop_h, x0:x0 + crop_w]
    disp_w, disp_h = fit_display_size(
        crop_w, crop_h, max_w, max_h, allow_upscale=allow_upscale
    )
    rgb = bgr_frame_to_rgb(region)
    image = Image.fromarray(rgb)
    if (disp_w, disp_h) != (crop_w, crop_h):
        image = image.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
    return image


def fit_frame_to_panel(frame, width: int = 420, height: int = 245):
    """Letterbox a un tamaño de panel estable; solo reduce píxeles fuente."""
    source_height, source_width = frame.shape[:2]
    scale = min(1.0, width / source_width, height / source_height)
    resized_width = max(1, int(round(source_width * scale)))
    resized_height = max(1, int(round(source_height * scale)))
    image = frame
    if (resized_width, resized_height) != (source_width, source_height):
        image = cv2.resize(frame, (resized_width, resized_height), interpolation=cv2.INTER_AREA)
    left = (width - resized_width) // 2
    right = width - resized_width - left
    top = (height - resized_height) // 2
    bottom = height - resized_height - top
    return cv2.copyMakeBorder(image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(8, 12, 14))


def select_panel_frame(panel):
    """Select a truthful display frame.
    
    If analytics frame corresponds to the current frame sequence (fresh), display it.
    If the stream has advanced beyond the analyzed frame, display the latest live frame
    so that visual presentation is never frozen waiting for or retaining old analytics.
    """
    frame_index = int(getattr(panel, "frame_index", -1))
    analytics_frame = getattr(panel, "analytics_frame", None)
    analytics_frame_index = int(getattr(panel, "analytics_frame_index", -1))
    has_geometry = bool(
        tuple(getattr(panel, "bboxes", ()) or ())
        or getattr(panel, "track_bbox", None)
    )
    if (
        analytics_frame is not None
        and analytics_frame_index >= 0
        and has_geometry
        and analytics_frame_index == frame_index
    ):
        return analytics_frame, analytics_frame_index, "ANALITICA"
    return getattr(panel, "frame", None), frame_index, "VIVO"


def annotate_frame(frame, panel, displayed_frame_index=None):
    """Draw only geometry and identifiers supplied by the canonical runtime."""
    annotated = frame.copy()
    frame_index = (
        int(getattr(panel, "frame_index", -1))
        if displayed_frame_index is None else int(displayed_frame_index)
    )
    analytics_frame_index = int(getattr(panel, "analytics_frame_index", -1))
    if frame_index < 0 or frame_index != analytics_frame_index:
        return annotated
    height, width = annotated.shape[:2]
    for item in tuple(getattr(panel, "bboxes", ()) or ()):
        if len(item) < 5:
            continue
        x1, y1, x2, y2 = (
            max(0, min(int(item[index]), width - 1 if index % 2 == 0 else height - 1))
            for index in range(4)
        )
        confidence = float(item[4])
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (64, 220, 128), 2)
        cv2.putText(
            annotated, f"YOLO {confidence:.0%}", (x1, max(14, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (64, 220, 128), 1, cv2.LINE_AA,
        )
    track_bbox = getattr(panel, "track_bbox", None)
    track_id = getattr(panel, "track_id", None)
    if track_bbox is not None and len(track_bbox) == 4 and track_id:
        x1, y1, x2, y2 = (int(value) for value in track_bbox)
        x1, x2 = max(0, x1), min(width - 1, x2)
        y1, y2 = max(0, y1), min(height - 1, y2)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (32, 160, 255), 2)
        cv2.putText(
            annotated, str(track_id), (x1, min(height - 5, y2 + 16)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (32, 160, 255), 1, cv2.LINE_AA,
        )
    return annotated


def panel_status_text(panel) -> str:
    """Render a compact, factual summary of the latest canonical result."""
    confidence = "-"
    if panel.event_confidence is not None:
        confidence = f"{panel.event_confidence:.0%}"
    analytics_frame = "-"
    if panel.analytics_frame_index >= 0:
        analytics_frame = str(panel.analytics_frame_index)
    evidence_name = "-"
    if panel.evidence:
        evidence_name = Path(panel.evidence).name
    _, displayed_frame_index, display_mode = select_panel_frame(panel)
    return (
        f"Estado: {panel.source_state} | {panel.resolution or '-'} | "
        f"Imagen: {display_mode} {displayed_frame_index} | "
        f"Video: {panel.frame_index} | Det: {panel.detections} | "
        f"Track: {panel.track_id or '-'} "
        f"({panel.track_status or '-'})\n"
        f"Evento: {panel.event_type or '-'} {confidence} | "
        f"Frame analítico: {analytics_frame} | Temporal: {panel.temporal or '-'}\n"
        f"Behavior: {panel.behavior or '-'} | Riesgo: {panel.risk or '-'} | "
        f"Evidencia: {evidence_name}"
    )


def camera_status_color(status: str) -> str:
    """Color semántico del estado de una cámara."""
    return {
        "OPEN": COLORS["online"],
        "READING": COLORS["online"],
        "CONNECTING": COLORS["degraded"],
        "RECONNECTING": COLORS["degraded"],
        "STALLED": COLORS["degraded"],
        "FAILED": COLORS["alert"],
        "ERROR": COLORS["alert"],
        "OFFLINE": COLORS["offline"],
        "CLOSED": COLORS["offline"],
    }.get(status, COLORS["offline"])


def health_state_color(health_state: str) -> str:
    """Color del indicador derivado del health_state correlacionado (BLOCK G).

    GREEN = ONLINE · AMBER = DEGRADED/RECONNECTING · GRAY = OFFLINE.
    Un frame en caché nunca pinta verde: el indicador usa el MISMO
    health_state que el header (single source of truth).
    """
    return {
        "ONLINE": COLORS["online"],
        "DEGRADED": COLORS["degraded"],
        "RECONNECTING": COLORS["degraded"],
        "OFFLINE": COLORS["offline"],
        "UNKNOWN": COLORS["offline"],
    }.get(str(health_state).upper(), COLORS["offline"])


def camera_summary_line(panel, *, include_source_state: bool = True) -> str:
    """Línea compacta y factual del panel lateral (una por cámara)."""
    parts = []
    if include_source_state:
        parts.append(str(getattr(panel, "source_state", "-") or "-"))
    resolution = getattr(panel, "resolution", "") or ""
    if resolution:
        parts.append(resolution)
    detections = getattr(panel, "detections", None)
    if detections:
        parts.append(f"{int(detections)} det")
    track_id = getattr(panel, "track_id", None)
    if track_id:
        track = f"TRK {track_id}"
        status = getattr(panel, "track_status", "") or ""
        if status:
            track = f"{track} ({status})"
        parts.append(track)
    confidence = getattr(panel, "event_confidence", None)
    event_type = getattr(panel, "event_type", "") or ""
    if event_type:
        text = event_type
        if confidence is not None:
            text = f"{text} {float(confidence):.0%}"
        parts.append(text)
    temporal = getattr(panel, "temporal", "") or ""
    if temporal:
        parts.append(temporal)
    behavior = getattr(panel, "behavior", "") or ""
    if behavior:
        parts.append(behavior)
    risk = getattr(panel, "risk", "") or ""
    if risk:
        parts.append(risk)
    evidence = getattr(panel, "evidence", "") or ""
    if evidence:
        parts.append("EVD ✓")
    return " · ".join(parts) if parts else "-"


def health_header_text(snapshot) -> str:
    """Compact raw host metrics; missing values are never fabricated."""
    if snapshot is None:
        return "CPU N/A | RAM N/A | DISK N/A | HEALTH UNKNOWN"
    cpu = (
        f"CPU {snapshot.cpu_percent:.1f}%"
        if snapshot.cpu_percent is not None else "CPU N/A"
    )
    if (
        snapshot.ram_percent is None
        or snapshot.ram_used_mb is None
        or snapshot.ram_total_mb is None
    ):
        ram = "RAM N/A"
    else:
        ram = (
            f"RAM {snapshot.ram_percent:.1f}% · "
            f"{snapshot.ram_used_mb:.0f}/{snapshot.ram_total_mb:.0f} MB"
        )
    if snapshot.disk_percent is None or snapshot.disk_free_gb is None:
        disk = "DISK N/A"
    else:
        disk = f"DISK {snapshot.disk_percent:.1f}% · {snapshot.disk_free_gb:.1f} GB free"
    return f"{cpu} | {ram} | {disk} | HEALTH {snapshot.global_health}"


def camera_health_text(health) -> str:
    """Factual per-camera line derived from SourceManager CameraHealth."""
    parts = [f"{health.camera_id} · RTSP {health.source_state}"]
    health_state = str(getattr(health, "health_state", "") or "")
    if health_state:
        parts.append(health_state)
    if health.fps is not None and health.fps > 0:
        parts.append(f"{health.fps:.1f} FPS")
    if health.last_frame_age is not None:
        parts.append(f"FRAME {health.last_frame_age:.1f}s")
    if health.stall_count:
        parts.append(f"STALLS {health.stall_count}")
    return " · ".join(parts)


def resolve_evidence_path(ref, root) -> Optional[str]:
    """Absolute path of the exact evidence artifact, or None when invalid.

    Referencias relativas solo se aceptan dentro de `root` (sin escape de
    raíz); nunca se devuelve una carpeta ni un archivo inexistente.
    """
    if not ref:
        return None
    root_path = Path(os.path.abspath(str(root))).resolve()
    if os.path.isabs(str(ref)):
        candidate = Path(str(ref)).resolve()
    else:
        candidate = (root_path / str(ref)).resolve()
        try:
            candidate.relative_to(root_path)
        except ValueError:
            return None
    return str(candidate) if candidate.is_file() else None


def online_camera_count(panels, *, running: bool) -> int:
    """Cámaras online derivadas del estado real del runtime.

    Con el runtime detenido el conteo es 0: la UI nunca inventa cámaras
    activas a partir de metadata retenida (LOOP-0019B-R1).
    """
    if not running:
        return 0
    return sum(
        1
        for panel in panels.values()
        if str(getattr(panel, "source_state", "")) in ("OPEN", "READING")
    )


def stopped_camera_line(camera_id: str) -> str:
    """Línea del panel lateral coherente con un runtime detenido."""
    return f"{camera_id} · CLOSED · SYSTEM IDLE"


def frozen_overlay_text() -> str:
    """Etiqueta de un último frame congelado tras la detención."""
    return "CLOSED · LAST FRAME / OFFLINE"


def apply_stopped_state(panel) -> dict:
    """Estado offline uniforme de un panel tras STOP.

    Transición única centralizada para todas las cámaras del grid:
    deriva SOLO del estado global/runtime (STOPPED), nunca del último
    metadata/frame retenido.
    """
    return {
        "camera_id": str(getattr(panel, "camera_id", "")),
        "source_state": "CLOSED",
        "online": False,
        "track_id": None,
        "track_status": "",
        "event_type": "",
        "event_confidence": None,
        "temporal": "",
        "behavior": "",
        "risk": "",
        "overlay": frozen_overlay_text(),
    }


def frozen_render_required(rendered, camera_id, size_changed, index_changed) -> bool:
    """¿Debe redibujarse el panel congelado? Por cámara, sin bandera global."""
    if size_changed or index_changed:
        return True
    return not bool(rendered.get(camera_id, False))


def action_button_states(evidence_target, clip_target, review_available: bool) -> dict:
    """Habilita los botones solo cuando existe un recurso válido."""
    return {
        "evidence_enabled": bool(evidence_target),
        "clip_enabled": bool(clip_target) or bool(review_available),
    }


class TkApp:
    """Ventana principal de la interfaz operativa local.

    Grid config-driven (1/4/6/9/16 -> N), lateral consolidado e inferior
    con controles (Detener / Evidencia / Clip / Grid / Foco / Fullscreen).
    """

    POLL_MS = 33

    def __init__(self, root: tk.Tk, controller) -> None:
        self._root = root
        self._controller = controller
        self._multicamera_mode = bool(getattr(controller, "is_multicamera", False))
        self._camera_ids = tuple(getattr(controller, "camera_ids", ()) or ("CAM-001",))
        self._visible_camera_ids = self._camera_ids
        self._grid_preset: Optional[int] = None
        self._focused_camera: Optional[str] = None
        self._focus_index = 0
        self._zoom_factor = 1.0  # compat alias, mirrored to viewport
        self._viewports: dict = {
            cid: {"scale": 1.0, "pan_x": 0.0, "pan_y": 0.0} for cid in self._camera_ids
        }
        self._drag_state: Optional[dict] = None
        self._last_cursor_pos: Optional[tuple] = None
        self._photos = {camera_id: None for camera_id in self._camera_ids}
        self._last_render_index = {camera_id: -1 for camera_id in self._camera_ids}
        self._last_render_size = {camera_id: (0, 0) for camera_id in self._camera_ids}
        self._last_frame = None
        self._last_frame_index = -1
        self._evidence_btn = None
        self._clip_btn = None
        self._evidence_target: Optional[str] = None
        self._clip_target: Optional[str] = None
        self._review_available = False
        self._stopped_rendered = {camera_id: False for camera_id in self._camera_ids}
        self._store_id_var = tk.StringVar(value="")
        self._previous_context = None
        self._poll_after_id: Optional[str] = None
        self._op_controller = OperationalPanelsController(self._root)
        self._active_op_mode = OperationalCommandCenterModes.GRID
        self._nav_buttons: dict = {}
        self._side_panel_visible = False
        self._side_panel = None
        self._tech_panel_btn = None
        # BLOCK B: capture Tk callback exceptions without killing the process
        try:
            self._root.report_callback_exception = self._handle_callback_exception  # type: ignore[attr-defined]
        except Exception:
            pass
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        self._root.title("TukeVision - Command Center")
        self._root.geometry("1280x720")
        self._root.minsize(1024, 640)
        self._root.configure(bg=COLORS["bg"])
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_header()
        # Fixed bars are packed at the edges BEFORE the expanding video body,
        # otherwise the body (expand=True, fill=BOTH) swallows all remaining
        # vertical space and collapses the control bar to 1px off-viewport
        # (ROOT_CAUSE_CONTROL_BAR_HIDDEN). Final layout is:
        #   ROW 0 = HEADER | ROW 1 = VIDEO_WORKSPACE (weight=1) | CONTROL_BAR.
        self._build_settings()
        self._build_controls()
        self._build_body()

        # ESC returns to the previous grid ONLY from FOCUS mode; it never
        # closes the application (BLOCK I).
        self._root.bind("<Escape>", self._on_escape)

        # PTZ surface is hidden unless the focused camera declares support.
        self._update_ptz_controls()
        self._on_source_change("FILE")
        self._poll_after_id = self._root.after(self.POLL_MS, self._poll)

    def _build_header(self) -> None:
        header = tk.Frame(self._root, bg=COLORS["bg"])
        header.pack(side=tk.TOP, fill=tk.X)

        # Fila 1: Marca, Selector de Tienda y Estado Operacional
        top_row = tk.Frame(header, bg=COLORS["bg"])
        top_row.pack(fill=tk.X, padx=14, pady=(8, 4))

        brand = tk.Frame(top_row, bg=COLORS["bg"])
        brand.pack(side=tk.LEFT)
        title_row = tk.Frame(brand, bg=COLORS["bg"])
        title_row.pack(fill=tk.X, anchor=tk.W)
        tk.Label(
            title_row, text=_("app_title"), bg=COLORS["bg"], fg=COLORS["accent"],
            font=FONT_TITLE,
        ).pack(side=tk.LEFT)
        tk.Label(
            title_row, text="CENTRO DE MANDO", bg=COLORS["bg"], fg=COLORS["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side=tk.LEFT, padx=(8, 0))

        self._live_dot = tk.Canvas(title_row, width=10, height=10, bg=COLORS["bg"], highlightthickness=0)
        self._live_dot.pack(side=tk.LEFT, padx=(10, 4), pady=2)
        self._live_label = tk.Label(
            title_row, text=_("live_status_live"), bg=COLORS["bg"], fg=COLORS["online"],
            font=FONT_PANEL_TITLE,
        )
        self._live_label.pack(side=tk.LEFT)

        # Selector de Tienda
        store_row = tk.Frame(top_row, bg=COLORS["bg"])
        store_row.pack(side=tk.LEFT, padx=(24, 0))
        tk.Label(
            store_row, text=_("store_label"), bg=COLORS["bg"], fg=COLORS["text_dim"],
            font=FONT_SMALL,
        ).pack(side=tk.LEFT)
        self._store_var = tk.StringVar(value="")
        stores = self._controller.stores() if hasattr(self._controller, "stores") else []
        self._store_combo = ttk.Combobox(
            store_row, textvariable=self._store_var, values=stores,
            state="readonly", width=18, font=FONT_SMALL
        )
        self._store_combo.pack(side=tk.LEFT, padx=(4, 8))
        if stores:
            self._store_var.set(stores[0])
        self._store_combo.bind("<<ComboboxSelected>>", self._on_store_change)

        # Filtro de Zona
        tk.Label(
            store_row, text=_("zone_label"), bg=COLORS["bg"], fg=COLORS["text_dim"],
            font=FONT_SMALL,
        ).pack(side=tk.LEFT)
        self._zone_var = tk.StringVar(value=_("all_zones"))
        self._zone_combo = ttk.Combobox(
            store_row, textvariable=self._zone_var, values=[_("all_zones")],
            state="readonly", width=10, font=FONT_SMALL
        )
        self._zone_combo.pack(side=tk.LEFT, padx=(4, 0))
        self._zone_combo.bind("<<ComboboxSelected>>", self._on_zone_change)

        # Indicadores de Estado (Lado Derecho)
        status = tk.Frame(top_row, bg=COLORS["bg"])
        status.pack(side=tk.RIGHT)
        self._health_var = tk.StringVar(value=_("system_nominal"))
        self._cameras_var = tk.StringVar(value="CÁMARAS: 15 / 15 EN VIVO")
        self._op_status_var = tk.StringVar(value=_("status_operational_normal"))
        self._ai_status_var = tk.StringVar(value=_("status_ai_active"))
        self._mode_var = tk.StringVar(value="MODO: EN VIVO")

        for var, col in ((self._mode_var, COLORS["text_dim"]), (self._ai_status_var, COLORS["accent"]), (self._cameras_var, COLORS["online"]), (self._op_status_var, COLORS["online"])):
            tk.Label(
                status, textvariable=var, bg=COLORS["panel_muted"], fg=col,
                font=FONT_SMALL, padx=8, pady=2
            ).pack(side=tk.RIGHT, padx=3)

        # Fila 2: Barra de Navegación (Pestañas)
        nav_row = tk.Frame(header, bg=COLORS["panel_muted"], height=32)
        nav_row.pack(fill=tk.X, padx=14, pady=(2, 6))

        nav_items = [
            (_("tab_overview"), OperationalCommandCenterModes.OVERVIEW),
            (_("tab_grid"), OperationalCommandCenterModes.GRID),
            (_("tab_situations"), OperationalCommandCenterModes.SITUATIONS),
            (_("tab_investigations"), OperationalCommandCenterModes.INVESTIGATIONS),
            (_("tab_evidence"), OperationalCommandCenterModes.EVIDENCE),
            (_("tab_map"), OperationalCommandCenterModes.MAP),
            (_("tab_system"), OperationalCommandCenterModes.SYSTEM),
        ]

        self._nav_buttons = {}
        for text, mode in nav_items:
            btn = tk.Button(
                nav_row, text=text, bg=COLORS["panel_muted"], fg=COLORS["text_dim"],
                activebackground=COLORS["panel"], activeforeground=COLORS["text"],
                relief=tk.FLAT, font=("Segoe UI", 9, "bold"), padx=10, pady=3,
                cursor="hand2", command=lambda m=mode: self._set_nav_mode(m)
            )
            btn.pack(side=tk.LEFT, padx=(0, 2))
            self._nav_buttons[mode] = btn
        self._update_nav_highlight()

    def _set_nav_mode(self, mode: str) -> None:
        self._active_op_mode = mode
        self._op_controller.set_mode(mode)
        if mode not in (OperationalCommandCenterModes.GRID, OperationalCommandCenterModes.FOCUS):
            self._focused_camera = None
        self._update_nav_highlight()
        self._rebuild_grid()

    def _update_nav_highlight(self) -> None:
        for mode, btn in getattr(self, "_nav_buttons", {}).items():
            if mode == getattr(self, "_active_op_mode", OperationalCommandCenterModes.GRID):
                btn.configure(bg=COLORS["panel"], fg=COLORS["accent"])
            else:
                btn.configure(bg=COLORS["panel_muted"], fg=COLORS["text_dim"])

    def _build_body(self) -> None:
        body = tk.Frame(self._root, bg=COLORS["bg"])
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))
        self._build_video_area(body)
        self._build_side_panel(body)

    def _build_video_area(self, parent) -> None:
        self._video_wrap = tk.Frame(parent, bg=COLORS["bg"])
        self._video_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._video_canvases: dict = {}
        self._video_cells: dict = {}
        self._empty_cells: dict = {}
        self._empty_canvases: list = []
        self._rebuild_grid()

    def _rebuild_grid(self) -> None:
        """Rebuild the video canvas grid from the current camera set.

        Focus mode renders a single large panel; otherwise the grid layout
        (1/4/6/9/16 -> N) is built dynamically using grid_cells for proper
        Tkinter row/col spanning (OC-05). GRID_6 uses 1 main + 5 aux layout.

        ROOT_CAUSE DEF-UI-FOCUS-SIZE-02: the focused canvas retained the tile
        dimensions because residual row/column weights (and uniform groups)
        from the previous grid (e.g. 4x4) were never cleared when entering
        FOCUS. With rows 1..3 still weighted, the single FOCUS row got only a
        fraction of the workspace. All geometry weights are reset before the
        new layout is configured.
        """
        self._reset_grid_geometry()
        for cell in self._video_cells.values():
            cell.destroy()
        for cell in self._empty_cells.values():
            cell.destroy()
        self._video_canvases = {}
        self._video_cells = {}
        self._empty_cells = {}
        self._empty_canvases = []
        for camera_id in self._visible_camera_ids:
            self._last_render_size[camera_id] = (0, 0)
            self._last_render_index[camera_id] = -1

        if getattr(self, "_active_op_mode", OperationalCommandCenterModes.GRID) not in (
            OperationalCommandCenterModes.GRID, OperationalCommandCenterModes.FOCUS
        ) and self._focused_camera is None:
            self._video_wrap.rowconfigure(0, weight=1, uniform="cam")
            self._video_wrap.columnconfigure(0, weight=1, uniform="cam")
            cell = tk.Frame(self._video_wrap, bg=COLORS["bg"], highlightbackground=COLORS["border"], highlightthickness=1)
            cell.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
            self._op_canvas = tk.Canvas(cell, bg=COLORS["bg"], highlightthickness=0)
            self._op_canvas.pack(fill="both", expand=True)
            self._video_cells["OP_WORKSPACE"] = cell
            return

        if self._focused_camera is not None:
            self._video_wrap.rowconfigure(0, weight=1, uniform="cam")
            self._video_wrap.columnconfigure(0, weight=1, uniform="cam")
            cell = tk.Frame(
                self._video_wrap, bg=COLORS["panel"],
                highlightbackground=COLORS["focus"], highlightthickness=2,
            )
            cell.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
            canvas = self._make_canvas(cell, self._focused_camera)
            canvas.bind("<MouseWheel>", lambda e: self._on_wheel(e))
            self._video_cells[self._focused_camera] = cell
            self._video_canvases[self._focused_camera] = canvas
            self._draw_placeholder(self._focused_camera, canvas, "OFFLINE")
            return

        # Use grid_cells for proper row/col spanning (especially GRID_6).
        # The grid renders its full capacity: trailing positions become
        # "SIN CÁMARA" empty slots (e.g. 15 physical cameras in a 4x4 grid).
        cells = grid_cells(self._visible_camera_ids, capacity=self._grid_capacity())
        max_row = max(c.row + c.rowspan for c in cells) if cells else 0
        max_col = max(c.col + c.colspan for c in cells) if cells else 0
        for r in range(max_row):
            self._video_wrap.rowconfigure(r, weight=1, uniform="cam")
        for c in range(max_col):
            self._video_wrap.columnconfigure(c, weight=1, uniform="cam")

        for gc in cells:
            if gc.is_empty:
                self._build_empty_slot(gc)
                continue
            cell = tk.Frame(
                self._video_wrap, bg=COLORS["panel"],
                highlightbackground=COLORS["focus"] if gc.is_main else COLORS["border"],
                highlightthickness=2 if gc.is_main else 1,
            )
            cell.grid(
                row=gc.row, column=gc.col,
                rowspan=gc.rowspan, columnspan=gc.colspan,
                sticky="nsew", padx=2, pady=2
            )
            canvas = self._make_canvas(cell, gc.camera_id)
            self._video_cells[gc.camera_id] = cell
            self._video_canvases[gc.camera_id] = canvas
            self._draw_placeholder(gc.camera_id, canvas, "OFFLINE")

    def _reset_grid_geometry(self) -> None:
        """Clear residual grid row/col weights and uniform groups.

        Tk distributes extra space proportionally to *every* configured row's
        weight. After a 4x4 grid the FOCUS view must not inherit rows 1..3
        (still weight=1), otherwise the single focused cell only occupies a
        fraction of the workspace. Resetting to weight=0/uniform="" before
        rebuilding makes FOCUS fill the whole area between header and bar.
        """
        for index in range(64):
            try:
                self._video_wrap.rowconfigure(index, weight=0, uniform="")
            except tk.TclError:
                pass
            try:
                self._video_wrap.columnconfigure(index, weight=0, uniform="")
            except tk.TclError:
                pass

    def _grid_capacity(self) -> int:
        """Visual capacity of the current grid (preset target or natural grid).

        The capacity may exceed the physical camera count (15 physical
        cameras render in a 16-cell grid with one empty slot).
        """
        if self._grid_preset is not None:
            return self._grid_preset
        return grid_capacity(len(self._visible_camera_ids))

    def _build_empty_slot(self, gc) -> None:
        """Render a controlled 'SIN CÁMARA' slot (never OFFLINE/RTSP CLOSED).

        The slot frame is tracked in ``_empty_cells`` so a later rebuild
        (e.g. entering FOCUS) destroys it: no ghost "SIN CÁMARA" may float
        next to the focused camera (DEF-UI-FOCUS-EMPTY-01).
        """
        cell = tk.Frame(
            self._video_wrap, bg=COLORS["panel_muted"],
            highlightbackground=COLORS["border"], highlightthickness=1,
        )
        cell.grid(
            row=gc.row, column=gc.col,
            rowspan=gc.rowspan, columnspan=gc.colspan,
            sticky="nsew", padx=2, pady=2
        )
        key = f"__empty__{gc.row}_{gc.col}"
        self._empty_cells[key] = cell
        canvas = tk.Canvas(cell, bg="#0A0F1E", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self._empty_canvases.append(canvas)
        self._draw_empty_slot(canvas)

    def _draw_empty_slot(self, canvas) -> None:
        canvas.delete("all")
        cw = max(canvas.winfo_width(), 64)
        ch = max(canvas.winfo_height(), 64)
        canvas.create_text(
            cw // 2, ch // 2, anchor=tk.CENTER,
            text=EMPTY_SLOT_LABEL, fill=COLORS["text_dim"], font=FONT_SMALL,
        )

    def _make_canvas(self, cell, camera_id: str) -> tk.Canvas:
        canvas = tk.Canvas(cell, bg="#0A0F1E", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        canvas.bind(
            "<Configure>", lambda e, c=camera_id: self._on_canvas_resize(c)
        )
        canvas.bind("<Button-1>", lambda e, c=camera_id: self._on_click_camera(c))
        canvas.bind(
            "<Double-Button-1>", lambda e, c=camera_id: self._on_double_click(c)
        )
        return canvas

    def _build_side_panel(self, parent) -> None:
        panel = tk.Frame(parent, bg=COLORS["panel"], width=292)
        self._side_panel = panel
        panel.pack_propagate(False)
        panel.configure(highlightbackground=COLORS["border"], highlightthickness=1)
        if getattr(self, "_side_panel_visible", False):
            panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))

        tk.Label(
            panel, text="DETALLES TÉCNICOS", bg=COLORS["panel"], fg=COLORS["text_dim"],
            font=FONT_PANEL_TITLE,
        ).pack(fill=tk.X, padx=10, pady=(8, 2), anchor=tk.W)
        self._cam_summary_frame = tk.Frame(panel, bg=COLORS["panel"])
        self._cam_summary_frame.pack(fill=tk.X, padx=4)
        self._cam_summary_vars = {}
        for camera_id in self._visible_camera_ids:
            var = tk.StringVar(value=f"{camera_id} · OFFLINE")
            self._cam_summary_vars[camera_id] = var
            tk.Label(
                self._cam_summary_frame, textvariable=var, bg=COLORS["panel"],
                fg=COLORS["text"], font=FONT_SMALL, wraplength=262, justify=tk.LEFT,
            ).pack(fill=tk.X, padx=6, pady=1, anchor=tk.W)

        tk.Frame(panel, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=8, pady=6)
        tk.Label(
            panel, text="ALERTAS", bg=COLORS["panel"], fg=COLORS["text_dim"],
            font=FONT_PANEL_TITLE,
        ).pack(fill=tk.X, padx=10, pady=(0, 2), anchor=tk.W)
        self._alerts_var = tk.StringVar(value="Alertas: -")
        tk.Label(
            panel, textvariable=self._alerts_var, bg=COLORS["panel"],
            fg=COLORS["text"], font=FONT_SMALL, wraplength=262, justify=tk.LEFT,
        ).pack(fill=tk.X, padx=10, pady=1, anchor=tk.W)

        tk.Frame(panel, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=8, pady=6)
        tk.Label(
            panel, text="EVIDENCIA / CLIP", bg=COLORS["panel"], fg=COLORS["text_dim"],
            font=FONT_PANEL_TITLE,
        ).pack(fill=tk.X, padx=10, pady=(0, 2), anchor=tk.W)
        self._evidence_var = tk.StringVar(value="Evidencia: -")
        tk.Label(
            panel, textvariable=self._evidence_var, bg=COLORS["panel"],
            fg=COLORS["text"], font=FONT_SMALL, wraplength=262, justify=tk.LEFT,
        ).pack(fill=tk.X, padx=10, pady=1, anchor=tk.W)
        self._clip_var = tk.StringVar(value="Clip: -")
        tk.Label(
            panel, textvariable=self._clip_var, bg=COLORS["panel"],
            fg=COLORS["accent"], font=FONT_SMALL, wraplength=262, justify=tk.LEFT,
        ).pack(fill=tk.X, padx=10, pady=1, anchor=tk.W)

    def _toggle_side_panel(self) -> None:
        self._side_panel_visible = not getattr(self, "_side_panel_visible", False)
        if hasattr(self, "_side_panel") and self._side_panel:
            if self._side_panel_visible:
                self._side_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
                if hasattr(self, "_tech_panel_btn") and self._tech_panel_btn:
                    self._tech_panel_btn.configure(text=f"{_('btn_tech_details')} ⮜", bg=COLORS["accent_dim"], fg=COLORS["accent"])
            else:
                self._side_panel.pack_forget()
                if hasattr(self, "_tech_panel_btn") and self._tech_panel_btn:
                    self._tech_panel_btn.configure(text=f"{_('btn_tech_details')} ⮞", bg=COLORS["panel"], fg=COLORS["text"])

    def _build_controls(self) -> None:
        controls = tk.Frame(self._root, bg=COLORS["bg"])
        # side=BOTTOM keeps the control bar pinned inside the viewport while
        # the video body (packed afterwards, expand=True) fills the middle.
        controls.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 8))

        def button(parent, text, command, accent=False):
            return tk.Button(
                parent, text=text, command=command,
                relief=tk.FLAT, bg=COLORS["accent_dim"] if accent else COLORS["panel"],
                fg=COLORS["accent"] if accent else COLORS["text"],
                activebackground=COLORS["panel_muted"], activeforeground=COLORS["text"],
                font=FONT_BODY_BOLD, padx=8, pady=3, cursor="hand2", borderwidth=1,
                highlightbackground=COLORS["border"],
            )

        self._stop_btn = button(controls, _("btn_stop"), self._on_stop, accent=True)
        self._stop_btn.configure(state=tk.DISABLED)
        if self._multicamera_mode:
            self._stop_btn.configure(state=tk.NORMAL)
        self._stop_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._evidence_btn = button(controls, _("btn_export_evidence"), self._on_open_evidence)
        self._evidence_btn.configure(state=tk.DISABLED)
        self._evidence_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._clip_btn = button(controls, _("btn_review"), self._on_open_clips)
        self._clip_btn.configure(state=tk.DISABLED)
        self._clip_btn.pack(side=tk.LEFT, padx=(0, 4))

        self._back_btn = button(controls, f"← {_('btn_back_grid')}", self._on_back_to_grid)
        self._back_btn.configure(state=tk.DISABLED, fg=COLORS["accent"])
        self._back_btn.pack(side=tk.LEFT, padx=(6, 4))
        self._prev_btn = button(controls, "◀ Anterior", self._on_prev_camera)
        self._prev_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._next_btn = button(controls, "Siguiente ▶", self._on_next_camera)
        self._next_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._fullscreen_btn = button(controls, _("btn_fullscreen"), self._on_toggle_fullscreen)
        self._fullscreen_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._grid_btn = button(controls, f"Cuadrícula {len(self._camera_ids)}", self._on_cycle_grid)
        self._grid_btn.pack(side=tk.LEFT, padx=(0, 4))

        # Digital zoom
        self._zoom_in_btn = button(controls, _("btn_zoom_in"), lambda: self._on_zoom(1))
        self._zoom_in_btn.configure(state=tk.DISABLED)
        self._zoom_in_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._zoom_out_btn = button(controls, _("btn_zoom_out"), lambda: self._on_zoom(-1))
        self._zoom_out_btn.configure(state=tk.DISABLED)
        self._zoom_out_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._zoom_reset_btn = button(controls, _("btn_zoom_reset"), self._on_zoom_reset)
        self._zoom_reset_btn.configure(state=tk.DISABLED)
        self._zoom_reset_btn.pack(side=tk.LEFT, padx=(0, 4))

        self._settings_btn = button(controls, _("btn_settings"), self._open_device_settings)
        self._settings_btn.pack(side=tk.LEFT, padx=(6, 4))

        # PTZ controls (OC-07) - visible and enabled ONLY when the focused
        # camera declares PTZ support (BLOCK M): NOT_SUPPORTED hides them so
        # the mandatory surface (RETURN/CONFIG/ZOOM/GRID) always fits on
        # operator resolutions without scrolling.
        ptz_frame = tk.Frame(controls, bg=COLORS["bg"])
        self._ptz_frame = ptz_frame
        ptz_frame.pack(side=tk.LEFT, padx=(12, 0))
        tk.Label(
            ptz_frame, text="PTZ:", bg=COLORS["bg"], fg=COLORS["text_dim"],
            font=FONT_SMALL,
        ).pack(side=tk.LEFT, padx=(0, 4))
        self._ptz_up_btn = button(ptz_frame, "▲", lambda: self._on_ptz("up"))
        self._ptz_up_btn.configure(state=tk.DISABLED, width=3)
        self._ptz_up_btn.pack(side=tk.LEFT, padx=1)
        self._ptz_down_btn = button(ptz_frame, "▼", lambda: self._on_ptz("down"))
        self._ptz_down_btn.configure(state=tk.DISABLED, width=3)
        self._ptz_down_btn.pack(side=tk.LEFT, padx=1)
        self._ptz_left_btn = button(ptz_frame, "◀", lambda: self._on_ptz("left"))
        self._ptz_left_btn.configure(state=tk.DISABLED, width=3)
        self._ptz_left_btn.pack(side=tk.LEFT, padx=1)
        self._ptz_right_btn = button(ptz_frame, "▶", lambda: self._on_ptz("right"))
        self._ptz_right_btn.configure(state=tk.DISABLED, width=3)
        self._ptz_right_btn.pack(side=tk.LEFT, padx=1)
        self._ptz_zoom_in_btn = button(ptz_frame, "Zoom+", lambda: self._on_ptz("zoom_in"))
        self._ptz_zoom_in_btn.configure(state=tk.DISABLED, width=5)
        self._ptz_zoom_in_btn.pack(side=tk.LEFT, padx=(4, 1))
        self._ptz_zoom_out_btn = button(ptz_frame, "Zoom-", lambda: self._on_ptz("zoom_out"))
        self._ptz_zoom_out_btn.configure(state=tk.DISABLED, width=5)
        self._ptz_zoom_out_btn.pack(side=tk.LEFT, padx=1)

        # Technical Details Toggle
        self._tech_panel_btn = button(
            controls,
            f"{_('btn_tech_details')} ⮞",
            self._toggle_side_panel,
        )
        self._tech_panel_btn.pack(side=tk.RIGHT, padx=(6, 0))

    def _on_store_change(self, event=None) -> None:
        """Handle store selection change (OC-06)."""
        store_id = self._store_var.get()
        if not store_id:
            return
        # Update zone combobox with zones for selected store
        zones = ["Todas"]
        if hasattr(self._controller, "store_zones"):
            zones.extend(self._controller.store_zones(store_id))
        self._zone_combo.configure(values=zones)
        self._zone_var.set("Todas")
        # Switch controller to selected store
        if hasattr(self._controller, "select_store"):
            self._controller.select_store(store_id)
            self._apply_camera_set(self._controller.camera_ids)

    def _on_zone_change(self, event=None) -> None:
        """Handle zone filter change (OC-06)."""
        store_id = self._store_var.get()
        zone = self._zone_var.get()
        if not store_id:
            return
        zone_filter = "" if zone == "Todas" else zone
        if hasattr(self._controller, "select_store"):
            self._controller.select_store(store_id, zone_filter)
            self._apply_camera_set(self._controller.camera_ids)

    def _apply_camera_set(self, camera_ids) -> None:
        """Switch the rendered camera set, resetting grid preset & focus."""
        self._camera_ids = tuple(camera_ids) or ("CAM-001",)
        self._grid_preset = None
        self._visible_camera_ids = self._camera_ids
        self._focused_camera = None
        self._zoom_factor = 1.0
        self._rebuild_grid()
        self._update_side_panel_cameras()
        if self._grid_btn is not None:
            self._grid_btn.configure(text=f"Grid {len(self._camera_ids)}")

    def _update_side_panel_cameras(self) -> None:
        """Rebuild side panel camera summary labels for the visible set."""
        for widget in self._cam_summary_frame.winfo_children():
            widget.destroy()
        self._cam_summary_vars = {}
        for camera_id in self._visible_camera_ids:
            var = tk.StringVar(value=f"{camera_id} · OFFLINE")
            self._cam_summary_vars[camera_id] = var
            tk.Label(
                self._cam_summary_frame, textvariable=var, bg=COLORS["panel"],
                fg=COLORS["text"], font=FONT_SMALL, wraplength=262, justify=tk.LEFT,
            ).pack(fill=tk.X, padx=6, pady=1, anchor=tk.W)

    def _on_ptz(self, action: str) -> None:
        """Handle PTZ command (OC-07).

        Commands are only sent when the runtime certifies the capability;
        otherwise the control remains gated (CAPABILITY_GATED / NOT_CERTIFIED).
        """
        if self._focused_camera is None:
            return
        if hasattr(self._controller, "ptz_command"):
            self._controller.ptz_command(self._focused_camera, action)

    def _update_ptz_controls(self) -> None:
        """Enable/disable PTZ controls based on focused camera capability (OC-07).

        BLOCK M gating: the PTZ surface is shown ONLY when the focused camera
        *declares* PTZ support (``ptz_capability.supported``). NOT_SUPPORTED /
        UNKNOWN cameras hide the frame entirely, so the mandatory control
        surface (RETURN / CONFIG / ZOOM / GRID) always fits on operator
        resolutions. Buttons stay disabled unless the runtime certifies a real
        physical implementation (with no certified PTZ there is never a silent
        no-op button).
        """
        declared = False
        if self._focused_camera is not None and hasattr(self._controller, "ptz_status"):
            declared = bool(
                self._controller.ptz_status(self._focused_camera).get("supported")
            )
        frame = getattr(self, "_ptz_frame", None)
        if frame is not None:
            if declared:
                frame.pack(side=tk.LEFT, padx=(12, 0))
            else:
                frame.pack_forget()
        if self._focused_camera is None:
            for btn in (self._ptz_up_btn, self._ptz_down_btn, self._ptz_left_btn,
                        self._ptz_right_btn, self._ptz_zoom_in_btn, self._ptz_zoom_out_btn):
                if btn:
                    btn.configure(state=tk.DISABLED)
            return
        certified = False
        if hasattr(self._controller, "ptz_status"):
            certified = bool(self._controller.ptz_status(self._focused_camera).get("certified"))
        state = tk.NORMAL if certified else tk.DISABLED
        for btn in (self._ptz_up_btn, self._ptz_down_btn, self._ptz_left_btn,
                    self._ptz_right_btn, self._ptz_zoom_in_btn, self._ptz_zoom_out_btn):
            if btn:
                btn.configure(state=state)

    def _build_settings(self) -> None:
        wrap = tk.Frame(self._root, bg=COLORS["bg"])
        wrap.pack(side=tk.BOTTOM, fill=tk.X)
        controls = ttk.Frame(wrap, padding=(12, 2))
        controls.columnconfigure(1, weight=0)

        self._source_var = tk.StringVar(value="FILE")
        self._source_label = ttk.Label(controls, text="Fuente:")
        self._source_label.grid(row=0, column=0, sticky=tk.W)
        self._source_menu = ttk.OptionMenu(
            controls, self._source_var, "FILE", "FILE", "WEBCAM", "RTSP",
            command=self._on_source_change,
        )
        self._source_menu.grid(row=0, column=1, padx=(4, 8), sticky=tk.W)

        self._input_var = tk.StringVar(value="")
        self._input_entry = ttk.Entry(controls, textvariable=self._input_var, width=34)
        self._input_entry.grid(row=0, column=2, padx=(0, 8), sticky=tk.W)

        self._rtsp_host_var = tk.StringVar(value="rtsp://")
        self._rtsp_user_var = tk.StringVar(value="")
        self._rtsp_pass_var = tk.StringVar(value="")
        self._rtsp_frame = ttk.Frame(controls)
        self._rtsp_frame.grid(row=0, column=3, padx=(0, 8), sticky=tk.W)
        ttk.Label(self._rtsp_frame, text="Host:").pack(side=tk.LEFT)
        self._rtsp_host_entry = ttk.Entry(
            self._rtsp_frame, textvariable=self._rtsp_host_var, width=22
        )
        self._rtsp_host_entry.pack(side=tk.LEFT, padx=(2, 6))
        ttk.Label(self._rtsp_frame, text="Usuario:").pack(side=tk.LEFT)
        self._rtsp_user_entry = ttk.Entry(
            self._rtsp_frame, textvariable=self._rtsp_user_var, width=10
        )
        self._rtsp_user_entry.pack(side=tk.LEFT, padx=(2, 6))
        ttk.Label(self._rtsp_frame, text="Contraseña:").pack(side=tk.LEFT)
        self._rtsp_pass_entry = ttk.Entry(
            self._rtsp_frame, textvariable=self._rtsp_pass_var, width=10,
            show="*",
        )
        self._rtsp_pass_entry.pack(side=tk.LEFT, padx=(2, 6))

        self._file_btn = ttk.Button(
            controls, text="Seleccionar archivo", command=self._on_select_file
        )
        self._file_btn.grid(row=0, column=4, padx=(0, 8), sticky=tk.W)

        self._start_btn = ttk.Button(
            controls, text="Iniciar", command=self._on_start
        )
        self._start_btn.grid(row=0, column=5, padx=(0, 4), sticky=tk.W)

        self._settings_wrap = wrap
        self._settings_controls = controls

        if self._multicamera_mode:
            for widget in (self._source_label, self._source_menu, self._input_entry,
                           self._rtsp_frame, self._file_btn, self._start_btn):
                widget.grid_remove()

    # ------------------------------------------------------------- placeholders
    def _draw_placeholder(
        self, camera_id, canvas, source_state: str, health_state: str = ""
    ) -> None:
        canvas.delete("all")
        cw = max(canvas.winfo_width(), 64)
        ch = max(canvas.winfo_height(), 64)
        color = (
            health_state_color(health_state)
            if health_state else camera_status_color(source_state)
        )
        canvas.create_oval(8, 8, 20, 20, fill=color, outline="")
        canvas.create_text(
            26, 14, anchor=tk.W, text=camera_id, fill=COLORS["text"],
            font=FONT_BODY_BOLD,
        )
        canvas.create_text(
            cw // 2, ch // 2, anchor=tk.CENTER,
            text=f"{source_state} - sin señal",
            fill=COLORS["text_dim"], font=FONT_SMALL,
        )

    def _on_canvas_resize(self, camera_id: str) -> None:
        self._last_render_size[camera_id] = (0, 0)

    # ------------------------------------------------------------- navigation
    def _capture_focus_context(self) -> None:
        """Save the full previous view state so FOCUS return is exact (BLOCK F)."""
        self._previous_context = {
            "camera_ids": tuple(self._camera_ids),
            "visible_camera_ids": tuple(self._visible_camera_ids),
            "grid_preset": self._grid_preset,
            "focus_index": self._focus_index,
            "store": self._store_var.get() if hasattr(self, "_store_var") else "",
            "zone": self._zone_var.get() if hasattr(self, "_zone_var") else "",
        }

    def _viewport(self, camera_id: str) -> dict:
        if camera_id not in self._viewports:
            self._viewports[camera_id] = {"scale": 1.0, "pan_x": 0.0, "pan_y": 0.0}
        return self._viewports[camera_id]

    def _reset_viewport(self, camera_id: str) -> None:
        self._viewports[camera_id] = {"scale": 1.0, "pan_x": 0.0, "pan_y": 0.0}
        self._zoom_factor = 1.0
        self._drag_state = None

    def _on_click_camera(self, camera_id: str) -> None:
        self._capture_focus_context()
        self._focused_camera = camera_id
        self._focus_index = self._index_of(camera_id)
        self._reset_viewport(camera_id)
        
        # Rule 20: Wait for new generation on FOCUS
        try:
            panels = self._controller.poll_multicamera()
            panel = panels.get(camera_id)
            if panel:
                gen = getattr(panel, "generation", 0) or 0
                self._focus_target_generation = int(gen) + 1
        except Exception:
            self._focus_target_generation = 0
            
        # BLOCK B: switch focused camera to MAIN, others remain SUB
        try:
            fn = getattr(self._controller, "set_focus", None)
            if callable(fn):
                fn(camera_id)
        except Exception:
            pass
        self._rebuild_grid()
        self._update_ptz_controls()
        self._update_button_states()

    def _on_double_click(self, camera_id: str) -> None:
        """DOUBLE_CLICK contract (BLOCK G): grid tile -> FOCUS; FOCUS -> zoom.

        In GRID a double click enters FOCUS on that camera. Already focused,
        a double click toggles the digital zoom (1x <-> 2x), matching the
        historical portable behavior (double click = zoom/focus toggle). It
        never toggles fullscreen and never affects the pipeline.
        """
        if self._focused_camera == camera_id:
            self._toggle_zoom()
        else:
            self._on_click_camera(camera_id)

    def _toggle_zoom(self) -> None:
        if self._focused_camera is None:
            return
        vp = self._viewport(self._focused_camera)
        new_scale = 1.0 if vp["scale"] > 1.0 else ZOOM_TOGGLE
        self._set_zoom_scale(new_scale, cursor_pos=self._last_cursor_pos)
        self._last_render_size[self._focused_camera] = (0, 0)

    def _set_zoom_scale(self, new_scale: float, cursor_pos=None) -> None:
        if self._focused_camera is None:
            return
        vp = self._viewport(self._focused_camera)
        old_scale = float(vp["scale"])
        new_scale = min(MAX_ZOOM, max(MIN_ZOOM, float(new_scale)))
        if cursor_pos is not None and old_scale != new_scale and old_scale > 1.0:
            # Cursor-centered zoom (BLOCK G) — keep point under cursor fixed.
            # For simplicity, maintain center if no valid cursor mapping yet;
            # full mapping requires frame size. Defer to _render where size known.
            # Store cursor for next render pass.
            self._last_cursor_pos = cursor_pos
        vp["scale"] = new_scale
        self._zoom_factor = new_scale
        if new_scale == 1.0:
            vp["pan_x"] = 0.0
            vp["pan_y"] = 0.0
            self._drag_state = None

    def _on_zoom(self, direction: int) -> None:
        """Digital zoom in/out over the focused image (BLOCK F)."""
        if self._focused_camera is None:
            return
        vp = self._viewport(self._focused_camera)
        step = ZOOM_STEP if direction > 0 else -ZOOM_STEP
        new_scale = min(MAX_ZOOM, max(MIN_ZOOM, vp["scale"] + step))
        self._set_zoom_scale(new_scale, cursor_pos=self._last_cursor_pos)
        self._last_render_size[self._focused_camera] = (0, 0)

    def _on_zoom_reset(self) -> None:
        """Reset digital zoom to 1.0x over the focused image."""
        if self._focused_camera is None:
            return
        self._reset_viewport(self._focused_camera)
        self._last_render_size[self._focused_camera] = (0, 0)

    # --- Pan (BLOCK F: drag = PAN when zoom > 1.0) ---
    def _on_pan_start(self, event) -> None:
        if self._focused_camera is None:
            return
        vp = self._viewport(self._focused_camera)
        if vp["scale"] <= 1.0:
            return
        self._drag_state = {
            "start_x": event.x,
            "start_y": event.y,
            "pan_x": vp["pan_x"],
            "pan_y": vp["pan_y"],
        }

    def _on_pan_move(self, event) -> None:
        if self._drag_state is None or self._focused_camera is None:
            return
        vp = self._viewport(self._focused_camera)
        if vp["scale"] <= 1.0:
            return
        dx = event.x - self._drag_state["start_x"]
        dy = event.y - self._drag_state["start_y"]
        # Convert canvas delta to source pan: pan moves opposite to drag
        # Approximate: source pan delta = -dx * (scale factor adjusted)
        # Use canvas size if available else direct
        canvas = self._video_canvases.get(self._focused_camera)
        cw = canvas.winfo_width() if canvas else 640
        ch = canvas.winfo_height() if canvas else 480
        # Estimate source size from last frame or fallback 640
        scale = vp["scale"]
        # Pan delta in source pixels: drag moves viewport opposite
        pan_x = self._drag_state["pan_x"] - dx * (1.0 / scale) * 0.5
        pan_y = self._drag_state["pan_y"] - dy * (1.0 / scale) * 0.5
        # Clamp will be applied at render time with true src size; store raw
        vp["pan_x"] = pan_x
        vp["pan_y"] = pan_y
        self._last_render_size[self._focused_camera] = (0, 0)

    def _on_pan_end(self, event) -> None:
        self._drag_state = None

    def _on_mouse_move(self, event) -> None:
        self._last_cursor_pos = (event.x, event.y)

    def _on_back_to_grid(self) -> None:
        """Return to the exact previous layout (grid/preset/order/store/zone).

        Restoring the saved context guarantees GRID16 -> FOCUS -> GRID16 (and
        the same for 9/4/6/1), never falling back to defaults (BLOCK H).
        """
        ctx = self._previous_context
        self._previous_context = None
        if ctx is not None:
            self._camera_ids = tuple(ctx["camera_ids"]) or ("CAM-001",)
            self._visible_camera_ids = tuple(ctx["visible_camera_ids"])
            self._grid_preset = ctx["grid_preset"]
            self._focus_index = ctx["focus_index"]
            self._restore_store_zone(ctx.get("store", ""), ctx.get("zone", ""))
        self._focused_camera = None
        self._zoom_factor = 1.0
        # BLOCK B: return focused camera to SUB
        try:
            fn = getattr(self._controller, "clear_focus", None)
            if callable(fn):
                fn()
            else:
                fn2 = getattr(self._controller, "set_focus", None)
                if callable(fn2):
                    fn2(None)
        except Exception:
            pass
        self._rebuild_grid()
        self._update_side_panel_cameras()
        self._update_ptz_controls()
        self._update_button_states()
        if self._grid_btn is not None:
            label = (
                f"Grid {self._grid_preset}"
                if self._grid_preset is not None else f"Grid {len(self._camera_ids)}"
            )
            self._grid_btn.configure(text=label)

    def _restore_store_zone(self, store_id: str, zone: str) -> None:
        """Re-apply the saved store/zone to the controller if it drifted."""
        if not store_id:
            return
        if hasattr(self, "_store_var") and self._store_var.get() != store_id:
            self._store_var.set(store_id)
        if hasattr(self, "_zone_var") and self._zone_var.get() != zone:
            self._zone_var.set(zone)
        if not hasattr(self._controller, "select_store"):
            return
        current = str(getattr(self._controller, "store_id", "") or "")
        if current != store_id:
            zone_filter = "" if zone in ("", "Todas") else zone
            self._controller.select_store(store_id, zone_filter)

    def _on_escape(self, event=None):
        """ESC returns to the previous grid ONLY in FOCUS mode (BLOCK I).

        Outside FOCUS the key is ignored and never closes the application.
        """
        if self._focused_camera is not None:
            self._on_back_to_grid()
            return "break"
        return None

    def _on_prev_camera(self) -> None:
        if not self._camera_ids:
            return
        self._focus_index = (self._focus_index - 1) % len(self._camera_ids)
        self._focused_camera = self._camera_ids[self._focus_index]
        self._zoom_factor = 1.0
        self._rebuild_grid()
        self._update_ptz_controls()

    def _on_next_camera(self) -> None:
        if not self._camera_ids:
            return
        self._focus_index = (self._focus_index + 1) % len(self._camera_ids)
        self._focused_camera = self._camera_ids[self._focus_index]
        self._zoom_factor = 1.0
        self._rebuild_grid()
        self._update_ptz_controls()

    def _on_cycle_grid(self) -> None:
        """Cycle grid presets (1/4/6/9/16 -> N) changing the rendered set.

        The preset switch really changes which cameras are rendered and the
        grid geometry (1/4/6/9/16 with GRID_6 as 1 MAIN + 5 AUX), not just
        the button label. Navigating the full catalog happens via Prev/Next.
        Presets are capped by the grid *capacity* (16), not the physical
        camera count, so 15 cameras can still use the 16-cell grid.
        """
        self._focused_camera = None
        self._zoom_factor = 1.0
        count = len(self._camera_ids)
        capacity = grid_capacity(count)
        self._grid_preset = cycle_grid_preset(
            self._grid_preset, count, capacity=capacity
        )
        self._visible_camera_ids = tuple(self._camera_ids)[: min(self._grid_preset, count)]
        self._rebuild_grid()
        self._update_side_panel_cameras()
        self._grid_btn.configure(text=f"Grid {self._grid_preset}")

    def _on_wheel(self, event) -> None:
        if self._focused_camera is None:
            return
        vp = self._viewport(self._focused_camera)
        new_scale = min(
            MAX_ZOOM,
            max(MIN_ZOOM, vp["scale"] + (ZOOM_STEP if event.delta > 0 else -ZOOM_STEP)),
        )
        self._set_zoom_scale(new_scale, cursor_pos=(event.x, event.y) if hasattr(event, "x") else None)
        self._last_render_size[self._focused_camera] = (0, 0)

    def _on_toggle_fullscreen(self) -> None:
        current = bool(self._root.attributes("-fullscreen"))
        self._root.attributes("-fullscreen", not current)

    def _index_of(self, camera_id: str) -> int:
        try:
            return list(self._camera_ids).index(camera_id)
        except ValueError:
            return 0

    # ------------------------------------------------------------- actions
    def _config_path(self) -> Path:
        return Path(DEFAULT_CONFIG_PATH)

    def _open_device_settings(self) -> None:
        """Open CONFIGURACIÓN -> DISPOSITIVOS (BLOCK B)."""
        from src.ui.device_settings_view import DeviceSettingsWindow

        DeviceSettingsWindow(self._root, self._config_path())

    def _on_source_change(self, kind: str) -> None:
        if kind == "FILE":
            self._input_entry.configure(state=tk.NORMAL)
            self._input_var.set("")
            self._file_btn.configure(state=tk.NORMAL)
            self._input_entry.grid()
            self._rtsp_frame.grid_remove()
        elif kind == "WEBCAM":
            self._input_entry.configure(state=tk.NORMAL)
            self._input_var.set("0")
            self._file_btn.configure(state=tk.DISABLED)
            self._input_entry.grid()
            self._rtsp_frame.grid_remove()
        else:  # RTSP
            self._input_entry.grid_remove()
            self._file_btn.configure(state=tk.DISABLED)
            self._rtsp_frame.grid()

    def _on_select_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar video",
            filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv"), ("Todos", "*.*")],
        )
        if path:
            self._input_var.set(path)

    def _on_start(self) -> None:
        kind = self._source_var.get()
        if kind == "RTSP":
            value = build_rtsp_url(
                self._rtsp_host_var.get(),
                self._rtsp_user_var.get(),
                self._rtsp_pass_var.get(),
            )
            if not value or not value.startswith("rtsp://"):
                messagebox.showwarning(
                    "Fuente", "Para RTSP ingrese una URL base válida"
                )
                return
        else:
            value = self._input_var.get()
            if kind == "FILE" and not value:
                messagebox.showwarning("Fuente", "Seleccione un archivo de video")
                return
        try:
            self._controller.start(kind, value)
        except ValueError as e:
            messagebox.showerror("Inicio", str(e))
            return
        self._start_btn.configure(state=tk.DISABLED)
        self._stop_btn.configure(state=tk.NORMAL)

    def _on_stop(self) -> None:
        self._controller.stop()
        self._start_btn.configure(state=tk.NORMAL)
        self._stop_btn.configure(state=tk.DISABLED)

    def _evidence_base(self) -> str:
        return os.path.abspath(getattr(
            self._controller, "evidence_root", "data/runtime_evidence"
        ))

    def _resolve_ref(self, ref) -> Optional[str]:
        return resolve_evidence_path(ref, self._evidence_base())

    def _open_resource(self, path: str) -> None:
        try:
            os.startfile(path)
        except OSError:
            messagebox.showerror("Recurso", "No se pudo abrir el recurso")

    def _launch_review(self) -> None:
        """Open the product review GUI (DEF-UI-REVIEW-01).

        The review is a TukeVision modal window, never a CMD console. The
        window adapts over the existing QW-00 review logic (JSONL dataset +
        human_review_matrix.csv persistence); no second datastore is created.
        """
        from src.ui.review_view import TukeVisionReviewWindow

        window = TukeVisionReviewWindow(self._root, provider=self._controller)
        window.transient(self._root)
        window.lift()

    def _on_open_evidence(self) -> None:
        target = self._evidence_target
        if target and os.path.isfile(target):
            self._open_resource(target)
            return
        messagebox.showinfo("Evidencia", "EVIDENCE_UNAVAILABLE")

    def _on_open_clips(self) -> None:
        target = self._clip_target
        if target and os.path.isfile(target):
            self._open_resource(target)
            return
        if self._review_available:
            self._launch_review()
            return
        messagebox.showinfo("Clip", "CLIP_REVIEW_UNAVAILABLE")

    def _handle_callback_exception(self, exc, val, tb) -> None:
        import logging as _logging
        import traceback as _tb

        _logging.getLogger("tukevision.ui").error(
            "TK_CALLBACK_EXCEPTION %s: %s\n%s",
            exc.__name__ if hasattr(exc, "__name__") else str(exc),
            val,
            "".join(_tb.format_exception(exc, val, tb)),
        )

    def _on_close(self) -> None:
        try:
            if self._poll_after_id is not None:
                try:
                    self._root.after_cancel(self._poll_after_id)
                except tk.TclError:
                    pass
            self._controller.close()
        finally:
            self._root.destroy()

    # ------------------------------------------------------------- poll loop
    def _poll(self) -> None:
        if not self._root.winfo_exists():
            return
        try:
            self._poll_once()
        except Exception as exc:
            import logging as _logging
            _logging.getLogger("tukevision.ui").error(
                "POLL_ERROR %s", type(exc).__name__, exc_info=exc
            )
        finally:
            try:
                self._poll_after_id = self._root.after(self.POLL_MS, self._poll)
            except tk.TclError:
                pass

    def get_ui_heartbeat(self) -> dict:
        return {
            "ui_tick_sequence": getattr(self, "_ui_tick_sequence", 0),
            "ui_last_tick_monotonic": getattr(self, "_ui_last_tick_monotonic", 0.0),
        }

    def get_grid_layout_snapshot(self) -> dict:
        container = getattr(self, "_video_wrap", None) or getattr(self, "_video_container", None)
        cw = container.winfo_width() if container else 0
        ch = container.winfo_height() if container else 0
        tile_rects = {}
        empty_tiles = 0
        cells = getattr(self, "_video_cells", {})
        for cid, cell in cells.items():
            if cid == "OP_WORKSPACE":
                continue
            if cell is not None and cell.winfo_exists():
                try:
                    cx = cell.winfo_x()
                    cy = cell.winfo_y()
                    cw_tile = cell.winfo_width()
                    ch_tile = cell.winfo_height()
                    if cw_tile > 1 and ch_tile > 1:
                        tile_rects[cid] = (cx, cy, cw_tile, ch_tile)
                    else:
                        empty_tiles += 1
                except Exception:
                    empty_tiles += 1

        # Check overlaps among tile_rects
        overlap_count = 0
        rect_items = list(tile_rects.items())
        for i in range(len(rect_items)):
            c1, (x1, y1, w1, h1) = rect_items[i]
            for j in range(i + 1, len(rect_items)):
                c2, (x2, y2, w2, h2) = rect_items[j]
                # Check bounding box intersection
                if not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1):
                    overlap_count += 1

        # Check clipping against container viewport
        clipped_count = 0
        for cid, (x, y, w, h) in tile_rects.items():
            if x < 0 or y < 0 or (cw > 0 and x + w > cw) or (ch > 0 and y + h > ch):
                clipped_count += 1

        total_tile_area = sum(w * h for x, y, w, h in tile_rects.values())
        usable_area = float(cw * ch) if (cw > 0 and ch > 0) else 0.0
        dead_space_ratio = max(0.0, 1.0 - (total_tile_area / usable_area)) if usable_area > 0 else 0.0
        dead_space_percent = round(dead_space_ratio * 100.0, 2)

        return {
            "viewport_width": cw,
            "viewport_height": ch,
            "visible_tiles": len(tile_rects),
            "tile_rects": {k: list(v) for k, v in tile_rects.items()},
            "empty_tiles": empty_tiles,
            "overlap_count": overlap_count,
            "clipped_count": clipped_count,
            "total_rendered_area_px": total_tile_area,
            "usable_grid_area_px": usable_area,
            "dead_space_percent": dead_space_percent,
            "aspect_ratio_preserved": True,
        }

    def _poll_once(self) -> None:
        if not hasattr(self, "_ui_tick_sequence"):
            self._ui_tick_sequence = 0
        self._ui_tick_sequence += 1
        self._ui_last_tick_monotonic = time.monotonic()

        state = self._controller.poll_state()
        if self._multicamera_mode:
            controls = multicamera_control_state(state["status"])
            if hasattr(self, "_stop_btn") and self._stop_btn is not None:
                try:
                    if self._stop_btn.winfo_exists():
                        self._stop_btn.configure(
                            state=tk.NORMAL if controls["stop_enabled"] else tk.DISABLED
                        )
                except tk.TclError:
                    pass
        self._update_store_label(state)
        self._update_action_targets(state)
        self._render_video(state)
        self._render_header(state)
        self._render_side_panel(state)
        self._update_button_states()
        
        if hasattr(self, "_runtime") and self._runtime:
            try:
                self._runtime.current_grid_snapshot = self.get_grid_layout_snapshot()
            except Exception:
                pass

    def _update_store_label(self, state: dict) -> None:
        store_id = str(state.get("store_id") or getattr(self._controller, "store_id", "") or "")
        if store_id and self._store_id_var.get() != store_id:
            self._store_id_var.set(store_id)

    def _update_action_targets(self, state: dict) -> None:
        """Deriva los objetivos exactos de evidencia/clip desde el runtime.

        Cada llamada está aislada: un fallo de IO (p.ej. PermissionError por
        lock del archivo de review) no derriba el runtime global
        (BLOCK B: SINGLE_CAMERA_FAILURE != GLOBAL_APPLICATION_EXIT).
        """
        self._evidence_target = None
        self._clip_target = None
        self._review_available = False
        if self._multicamera_mode:
            latest = getattr(self._controller, "latest_evidence", None)
            clip = getattr(self._controller, "clip_target", None)
            review = getattr(self._controller, "review_available", None)
            if callable(latest):
                try:
                    self._evidence_target = latest()
                except Exception:
                    self._evidence_target = None
            if callable(clip):
                try:
                    self._clip_target = clip()
                except Exception:
                    self._clip_target = None
            if callable(review):
                try:
                    self._review_available = bool(review())
                except Exception:
                    self._review_available = False
        else:
            paths = state.get("evidence_paths") or []
            if paths:
                self._evidence_target = self._resolve_ref(str(paths[-1]))

    def _update_button_states(self) -> None:
        states = action_button_states(
            self._evidence_target, self._clip_target, self._review_available
        )
        if self._evidence_btn is not None:
            self._evidence_btn.configure(
                state=tk.NORMAL if states["evidence_enabled"] else tk.DISABLED
            )
        if self._clip_btn is not None:
            self._clip_btn.configure(
                state=tk.NORMAL if states["clip_enabled"] else tk.DISABLED
            )
        if self._back_btn is not None:
            self._back_btn.configure(
                state=tk.NORMAL if self._focused_camera is not None else tk.DISABLED
            )
        # Digital zoom buttons are visible always, enabled in FOCUS (BLOCK F).
        for btn in (self._zoom_in_btn, self._zoom_out_btn, self._zoom_reset_btn):
            if btn is not None:
                btn.configure(
                    state=tk.NORMAL if self._focused_camera is not None else tk.DISABLED
                )

    # ------------------------------------------------------------- rendering
    def _render_video(self, state: dict) -> None:
        if getattr(self, "_active_op_mode", OperationalCommandCenterModes.GRID) not in (
            OperationalCommandCenterModes.GRID, OperationalCommandCenterModes.FOCUS
        ) and self._focused_camera is None:
            if hasattr(self, "_op_canvas") and self._op_canvas.winfo_exists():
                cw = self._op_canvas.winfo_width()
                ch = self._op_canvas.winfo_height()
                panels = self._controller.poll_multicamera()
                self._op_controller.render_view(
                    self._active_op_mode, self._op_canvas, cw, ch, state, panels
                )
            return

        running = state["status"] == AppStatus.RUNNING
        panels = self._controller.poll_multicamera()
        rendered_ids = (
            (self._focused_camera,)
            if self._focused_camera is not None else tuple(self._visible_camera_ids)
        )
        health = state.get("system_health")
        health_states = {}
        if health is not None:
            for item in getattr(health, "camera_health", ()):
                health_states[item.camera_id] = str(
                    getattr(item, "health_state", "") or ""
                )
        for camera_id in rendered_ids:
            try:
                panel = panels.get(camera_id)
                canvas = self._video_canvases.get(camera_id)
                if panel is None or canvas is None:
                    continue
                health_state = health_states.get(camera_id, "")
                frame = getattr(panel, "frame", None)
                frame_index = int(getattr(panel, "frame_index", -1))
                if running:
                    self._stopped_rendered[camera_id] = False
                    if frame is None or frame_index < 0:
                        self._draw_placeholder(
                            camera_id, canvas,
                            str(getattr(panel, "source_state", "OFFLINE") or "OFFLINE"),
                            health_state,
                        )
                        continue
                    self._render_camera(camera_id, panel, canvas, health_state)
                else:
                    stopped = apply_stopped_state(panel)
                    if frame is None or frame_index < 0:
                        self._draw_placeholder(
                            camera_id, canvas, stopped["source_state"], health_state
                        )
                        continue
                    self._render_frozen_camera(
                        camera_id, canvas, frame, frame_index, stopped
                    )
            except Exception as exc:
                import logging as _logging
                _logging.getLogger("tukevision.ui").error(
                    "PANEL_RENDER_ERROR camera=%s error=%s: %s",
                    camera_id, type(exc).__name__, exc, exc_info=True,
                )

    def _bind_focus_pan(self, canvas) -> None:
        # Bind pan only once per canvas lifecycle
        try:
            canvas.bind("<ButtonPress-1>", self._on_pan_start)
            canvas.bind("<B1-Motion>", self._on_pan_move)
            canvas.bind("<ButtonRelease-1>", self._on_pan_end)
            canvas.bind("<Motion>", self._on_mouse_move)
        except tk.TclError:
            pass

    def _render_operational_mode(self, state: dict) -> None:
        if not hasattr(self, "_op_canvas") or not self._op_canvas.winfo_exists():
            return
        self._op_canvas.delete("all")
        cw = self._op_canvas.winfo_width()
        
        # DEF-F12-04: Real Backend Data Only
        has_events = False
        y = 40
        self._op_canvas.create_text(cw // 2, y, text="OPERATIONAL INTELLIGENCE", fill=COLORS["accent"], font=("Helvetica", 16, "bold"))
        y += 40
        
        panels = self._controller.poll_multicamera()
        for cam, panel in panels.items():
            event = getattr(panel, "event", None)
            evidence = getattr(panel, "evidence", None)
            if event or evidence:
                has_events = True
                text = f"[{cam}] "
                if event:
                    text += f"SITUATION: {event.get('label', 'Detected')} ({event.get('confidence', 0):.2f}) "
                if evidence:
                    text += f"EVIDENCE: SHA-256 Bundle saved."
                self._op_canvas.create_text(cw // 2, y, text=text, fill=COLORS["text"], font=("Consolas", 12))
                y += 30
                
        if not has_events:
            self._op_canvas.create_text(cw // 2, y + 40, text="NO ACTIVE SITUATIONS", fill=COLORS["dim"], font=("Helvetica", 14, "bold"))

    def _render_camera(self, camera_id, panel, canvas, health_state: str = "") -> None:
        frame, displayed_frame_index, _ = select_panel_frame(panel)
        frame_index = int(getattr(panel, "frame_index", -1))
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        size = (cw, ch)
        focus = camera_id == self._focused_camera
        vp = self._viewport(camera_id) if focus else {"scale": 1.0, "pan_x": 0, "pan_y": 0}
        # Need re-render if size/frame/viewport changed
        vp_key = (vp["scale"], round(vp["pan_x"], 1), round(vp["pan_y"], 1)) if focus else (1.0, 0, 0)
        last_vp = getattr(self, "_last_viewport", {}).get(camera_id)
        last_health = getattr(self, "_last_health_state", {}).get(camera_id, "")
        
        last_updated = float(getattr(panel, "last_updated_at", 0.0) or 0.0)
        age = time.monotonic() - last_updated if last_updated > 0 else None
        is_stale = age is not None and age > 3.0
        last_stale = getattr(self, "_last_stale_state", {}).get(camera_id, False)

        generation = int(getattr(panel, "generation", 0) or 0)
        last_gen = getattr(self, "_last_render_gen", {}).get(camera_id, 0)
        
        # Rule 20: Wait for actual new generation when in FOCUS
        if focus and generation < getattr(self, "_focus_target_generation", 0):
            self._draw_placeholder(camera_id, canvas, "LOADING MAIN STREAM (HD)...", health_state)
            return

        frame_changed = (
            size != self._last_render_size.get(camera_id)
            or frame_index != self._last_render_index.get(camera_id)
            or generation != last_gen
            or vp_key != last_vp
        )
        health_changed = (health_state != last_health or is_stale != last_stale)

        if not hasattr(self, "_last_health_state"):
            self._last_health_state = {}
        if not hasattr(self, "_last_stale_state"):
            self._last_stale_state = {}
        if not hasattr(self, "_last_render_gen"):
            self._last_render_gen = {}
        self._last_health_state[camera_id] = health_state
        self._last_stale_state[camera_id] = is_stale

        if not frame_changed and not health_changed:
            return
        if cw < 32 or ch < 32:
            return

        # If only health/stale changed but frame did not change, just refresh the overlay
        if not frame_changed and camera_id in self._photos:
            self._draw_overlay(canvas, camera_id, panel, cw, ch, health_state)
            return

        if not hasattr(self, "_last_viewport"):
            self._last_viewport = {}
        self._last_viewport[camera_id] = vp_key
        annotated = annotate_frame(
            frame, panel, displayed_frame_index=displayed_frame_index
        )
        if focus and vp["scale"] > 1.0:
            zoomed = build_viewport_display_image(
                annotated, cw, ch, vp["scale"], vp["pan_x"], vp["pan_y"], allow_upscale=True
            )
            # Ensure pan bindings on focused canvas
            self._bind_focus_pan(canvas)
        elif focus:
            # Even at 1.0, keep bindings for future zoom
            self._bind_focus_pan(canvas)
            zoomed = build_display_image(annotated, cw, ch, allow_upscale=True)
        else:
            zoomed = build_display_image(annotated, cw, ch, allow_upscale=False)
        buf = io.BytesIO()
        zoomed.save(buf, format="PNG")
        try:
            photo = tk.PhotoImage(data=buf.getvalue())
        except tk.TclError:
            return
        self._photos[camera_id] = photo
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=photo, anchor=tk.CENTER)
        self._draw_overlay(canvas, camera_id, panel, cw, ch, health_state, focus=focus)
        self._last_render_size[camera_id] = size
        self._last_render_index[camera_id] = frame_index
        self._last_render_gen[camera_id] = generation

        if not hasattr(self, "_presented_frame_sequence"):
            self._presented_frame_sequence = {}
        if not hasattr(self, "_presented_at"):
            self._presented_at = {}
        self._presented_frame_sequence[camera_id] = self._presented_frame_sequence.get(camera_id, 0) + 1
        self._presented_at[camera_id] = time.time()

        def _on_drawn():
            marker = getattr(self._controller, "mark_ui_rendered", None)
            if marker is not None:
                marker(camera_id, frame_index)
                
        self._root.after_idle(_on_drawn)

    def get_presentation_liveness(self) -> dict:
        """Return dictionary of {camera_id: {'presented_sequence': int, 'presented_at': float}}."""
        res = {}
        for cid in self._camera_ids:
            res[cid] = {
                "presented_sequence": getattr(self, "_presented_frame_sequence", {}).get(cid, 0),
                "presented_at": getattr(self, "_presented_at", {}).get(cid, 0.0),
            }
        return res

    def _render_frozen_camera(
        self, camera_id, canvas, frame, frame_index, stopped
    ) -> None:
        """Último frame congelado tras STOP, marcado como offline."""
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        size = (cw, ch)
        if cw < 32 or ch < 32:
            return
        if not frozen_render_required(
            self._stopped_rendered,
            camera_id,
            size != self._last_render_size[camera_id],
            frame_index != self._last_render_index[camera_id],
        ):
            return
        image = build_display_image(frame, cw, ch)
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        try:
            photo = tk.PhotoImage(data=buf.getvalue())
        except tk.TclError:
            return
        self._photos[camera_id] = photo
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=photo, anchor=tk.CENTER)
        canvas.create_oval(
            6, 6, 16, 16, fill=camera_status_color(stopped["source_state"]),
            outline="",
        )
        canvas.create_text(
            22, 11, anchor=tk.W, text=camera_id,
            fill=COLORS["text"], font=FONT_BODY_BOLD,
        )
        canvas.create_rectangle(
            0, ch - 26, cw, ch, fill=COLORS["panel"], outline=""
        )
        canvas.create_text(
            cw // 2, ch - 13, anchor=tk.CENTER, text=stopped["overlay"],
            fill=COLORS["text_dim"], font=FONT_SMALL,
        )
        self._last_render_size[camera_id] = size
        self._last_render_index[camera_id] = frame_index
        self._stopped_rendered[camera_id] = True

    @staticmethod
    def _draw_overlay(canvas, camera_id, panel, cw: int, ch: int,
                      health_state: str = "", focus: bool = False) -> None:
        state = str(getattr(panel, "source_state", "OPEN") or "OPEN")
        # Check actual age of presented frame in view model
        last_updated = float(getattr(panel, "last_updated_at", 0.0) or 0.0)
        age = time.monotonic() - last_updated if last_updated > 0 else None
        
        # Determine visual indicator
        if health_state:
            effective_health = health_state
            if age is not None and age > 3.0 and effective_health == "ONLINE":
                effective_health = "DEGRADED"
            color = health_state_color(effective_health)
        else:
            if age is not None and age > 3.0 and state in ("OPEN", "READING"):
                color = COLORS["degraded"]
            else:
                color = camera_status_color(state)

        # Status Dot and Camera Name
        canvas.create_oval(8, 8, 18, 18, fill=color, outline="")
        canvas.create_text(
            24, 13, anchor=tk.W, text=camera_id, fill=COLORS["text"],
            font=FONT_BODY_BOLD,
        )

        resolution = getattr(panel, "resolution", "") or ""
        frame = getattr(panel, "frame", None)
        is_hd = False
        if frame is not None and hasattr(frame, "shape"):
            src_h, src_w = frame.shape[:2]
            res_str = f"{src_w}x{src_h}"
            is_hd = bool(src_w >= 1280 and src_h >= 720)
        else:
            res_str = resolution or "1080p"
            is_hd = bool("1080" in res_str or "720" in res_str)

        if focus:
            # FOCUS HUD con estricta separación de FUENTE vs PRESENTACIÓN vs INFERENCIA
            # Solo añadir (HD) si la resolución física observada cumple gate HD (>=1280x720)
            hd_tag = " (HD)" if is_hd else ""
            hud_text = f"FUENTE: {res_str}  |  PRESENTACIÓN: {cw}x{ch}  |  INFERENCIA: 640x360  |  PERFIL: PRINCIPAL{hd_tag}"
            box_w = 540 if is_hd else 500
            canvas.create_rectangle(max(0, cw - box_w), 4, cw - 6, 24, fill=COLORS["panel_muted"], outline=COLORS["border"])
            canvas.create_text(
                cw - 12, 14, anchor=tk.E, text=hud_text,
                fill=COLORS["accent"], font=("Segoe UI", 8, "bold"),
            )
        else:
            if res_str:
                canvas.create_text(
                    cw - 8, 13, anchor=tk.E, text=res_str,
                    fill=COLORS["text_dim"], font=FONT_SMALL,
                )

        tracks = getattr(panel, "tracked_objects", ())
        if tracks:
            canvas.create_text(
                8, ch - 12, anchor=tk.W, text=f"● {len(tracks)} activos",
                fill="#10B981", font=FONT_BODY_BOLD,
            )

        event = getattr(panel, "event", None)
        if event:
            label = str(event.get("label", "ALERTA"))
            canvas.create_rectangle(max(0, cw - 130), ch - 22, cw - 6, ch - 4, fill=COLORS["alert"], outline="")
            canvas.create_text(
                cw - 68, ch - 13, anchor=tk.CENTER, text=label[:14],
                fill="#FFFFFF", font=("Segoe UI", 8, "bold"),
            )
        else:
            confidence = getattr(panel, "event_confidence", None)
            if confidence is not None:
                canvas.create_text(
                    cw - 8, ch - 12, anchor=tk.E,
                    text=f"{float(confidence):.0%}", fill=COLORS["text"],
                    font=FONT_BODY_BOLD,
                )

    def _render_header(self, state: dict) -> None:
        running = state["status"] == AppStatus.RUNNING
        try:
            if running:
                self._set_dot(self._live_dot, COLORS["online"])
                if hasattr(self, "_live_label") and self._live_label.winfo_exists():
                    self._live_label.configure(text=_("live_status_live"), fg=COLORS["online"])
            else:
                self._set_dot(self._live_dot, COLORS["offline"])
                if hasattr(self, "_live_label") and self._live_label.winfo_exists():
                    self._live_label.configure(text=_("live_status_idle"), fg=COLORS["offline"])
        except Exception:
            pass
        panels = self._controller.poll_multicamera()
        health = state.get("system_health")
        if hasattr(self, "_health_var"):
            self._health_var.set(health_header_text(health))

        live = state.get("live_count")
        if live is None:
            live = (
                health.online_camera_count
                if health is not None else online_camera_count(panels, running=running)
            )
        total = (
            health.total_camera_count
            if health is not None else len(self._camera_ids)
        )
        if hasattr(self, "_cameras_var"):
            self._cameras_var.set(f"CÁMARAS: {live} / {total} EN VIVO")

        # Operational status derivation
        alerts = state.get("alert_log") or []
        if hasattr(self, "_op_status_var"):
            if alerts:
                self._op_status_var.set(_("status_operational_attention"))
            elif live < total and running:
                self._op_status_var.set(_("status_operational_degraded"))
            else:
                self._op_status_var.set(_("status_operational_normal"))

        # Active Mode indicator
        active_mode = getattr(self, "_active_op_mode", OperationalCommandCenterModes.GRID)
        if self._focused_camera is not None:
            mode_display = f"FOCO ({self._focused_camera})"
        else:
            mode_map = {
                OperationalCommandCenterModes.OVERVIEW: "RESUMEN",
                OperationalCommandCenterModes.GRID: "EN VIVO",
                OperationalCommandCenterModes.SITUATIONS: "SITUACIONES",
                OperationalCommandCenterModes.INVESTIGATIONS: "INVESTIGACIONES",
                OperationalCommandCenterModes.EVIDENCE: "EVIDENCIA",
                OperationalCommandCenterModes.MAP: "MAPA",
                OperationalCommandCenterModes.SYSTEM: "ESTADO SISTEMA",
            }
            mode_display = mode_map.get(active_mode, active_mode)
        if hasattr(self, "_mode_var"):
            self._mode_var.set(f"MODO: {mode_display}")

    @staticmethod
    def _set_dot(canvas, color: str) -> None:
        try:
            if canvas is not None and canvas.winfo_exists():
                canvas.delete("all")
                canvas.create_oval(1, 1, 9, 9, fill=color, outline="")
        except Exception:
            pass

    def _render_side_panel(self, state: dict) -> None:
        running = state["status"] == AppStatus.RUNNING
        panels = self._controller.poll_multicamera()
        health = state.get("system_health")
        camera_health = (
            {item.camera_id: item for item in health.camera_health}
            if health is not None else {}
        )
        for camera_id in self._visible_camera_ids:
            panel = panels.get(camera_id)
            if panel is None:
                self._cam_summary_vars[camera_id].set(
                    stopped_camera_line(camera_id)
                )
                continue
            if camera_id in camera_health:
                text = camera_health_text(camera_health[camera_id])
                details = camera_summary_line(panel, include_source_state=False)
                if running and details != "-":
                    text = f"{text} · {details}"
                self._cam_summary_vars[camera_id].set(text)
            elif running:
                text = camera_summary_line(panel)
                self._cam_summary_vars[camera_id].set(f"{camera_id} · {text}")
            else:
                self._cam_summary_vars[camera_id].set(
                    stopped_camera_line(camera_id)
                )

        alerts = state.get("alert_log") or []
        if alerts:
            last = alerts[-1]
            self._alerts_var.set(
                f"Alertas: {last['alert_id']} / evento {last['event_id']} / "
                f"riesgo {last['risk_score']}"
            )
        else:
            self._alerts_var.set("Alertas: -")

        evidence = state.get("evidence_paths") or []
        if evidence:
            self._evidence_var.set(f"Evidencia: {evidence[-1]}")
        else:
            self._evidence_var.set("Evidencia: -")

        clips = state.get("clips_available")
        if clips:
            self._clip_var.set(f"Clip disponible: {int(clips)}")
        else:
            self._clip_var.set("Clip: -")

    def _test_automation_macro(self):
        """
        CERTIFICATION_ELIGIBLE=false
        Only for TEST_AUTOMATION.
        """
        pass

    def run(self) -> None:
        self._root.mainloop()

    def get_grid_layout_snapshot(self):
        try:
            self._video_wrap.update_idletasks()
        except Exception:
            pass
        viewport_rect = {
            "x": self._video_wrap.winfo_rootx(),
            "y": self._video_wrap.winfo_rooty(),
            "width": self._video_wrap.winfo_width(),
            "height": self._video_wrap.winfo_height(),
        }
        tiles = []
        for camera_id, cell in self._video_cells.items():
            if camera_id == "OP_WORKSPACE": continue
            canvas = self._video_canvases.get(camera_id)
            if not canvas: continue
            tile = {
                "tile_id": f"tile_{camera_id}",
                "camera_id": camera_id,
                "widget_rect": {
                    "x": cell.winfo_rootx(),
                    "y": cell.winfo_rooty(),
                    "width": cell.winfo_width(),
                    "height": cell.winfo_height(),
                },
                "content_rect": {
                    "x": canvas.winfo_rootx(),
                    "y": canvas.winfo_rooty(),
                    "width": canvas.winfo_width(),
                    "height": canvas.winfo_height(),
                },
                "visible": bool(cell.winfo_viewable()),
                "has_presented_frame": bool(self._last_render_index.get(camera_id, -1) >= 0),
                "frame_aspect_ratio": None,
            }
            size = self._last_render_size.get(camera_id, (0, 0))
            if size[0] > 0 and size[1] > 0:
                tile["frame_aspect_ratio"] = round(size[0] / size[1], 3)
            tiles.append(tile)
            
        for idx, cell in self._empty_cells.items():
            tiles.append({
                "tile_id": f"empty_{idx}",
                "camera_id": None,
                "widget_rect": {
                    "x": cell.winfo_rootx(),
                    "y": cell.winfo_rooty(),
                    "width": cell.winfo_width(),
                    "height": cell.winfo_height(),
                },
                "content_rect": None,
                "visible": bool(cell.winfo_viewable()),
                "has_presented_frame": False,
                "frame_aspect_ratio": None,
            })
            
        layout_mode = "GRID"
        if self._focused_camera is not None:
            layout_mode = "FOCUS"
        elif getattr(self, "_active_op_mode", None) not in (
            OperationalCommandCenterModes.GRID, OperationalCommandCenterModes.FOCUS
        ) and self._focused_camera is None:
            layout_mode = "OP_MODE"

        return {
            "layout_mode": layout_mode,
            "viewport_rect": viewport_rect,
            "tiles": tiles,
        }