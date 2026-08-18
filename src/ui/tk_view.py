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

El frame de procesamiento nunca se modifica aquí; la presentación es una
vista que NO reescribe el pipeline, RTSP, YOLO ni tracking.
"""

import io
import os
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional
import tkinter as tk

import cv2
from PIL import Image

from src.capture.rtsp_url import build_rtsp_url
from src.ui.state import AppStatus
from src.ui.multicamera import CAMERA_IDS, PANEL_LAYOUT


# ---------------------------------------------------------------------------
# Design System (recoverado del Command Center portable, LOOP-0017B)
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
}

FONT_TITLE = ("Segoe UI", 15, "bold")
FONT_SUBTITLE = ("Segoe UI", 8)
FONT_PANEL_TITLE = ("Segoe UI", 9, "bold")
FONT_BODY = ("Segoe UI", 9)
FONT_BODY_BOLD = ("Segoe UI", 9, "bold")
FONT_SMALL = ("Segoe UI", 8)


def multicamera_control_state(status: str) -> dict:
    return {"show_legacy": False, "stop_enabled": status == AppStatus.RUNNING}


def fit_display_size(
    src_w: int, src_h: int, max_w: int, max_h: int
):
    """Tamaño de presentación que llena el área máxima sin deformar.

    Conserva la relación de aspecto y NUNCA escala por encima de la
    resolución de la fuente (sin fake upscale): si el área es mayor que la
    fuente, la imagen se muestra a resolución nativa y el Canvas la centra.
    """
    if src_w <= 0 or src_h <= 0 or max_w <= 0 or max_h <= 0:
        return int(src_w), int(src_h)
    scale = min(1.0, max_w / src_w, max_h / src_h)
    disp_w = max(1, int(round(src_w * scale)))
    disp_h = max(1, int(round(src_h * scale)))
    return disp_w, disp_h


def bgr_frame_to_rgb(frame):
    """Convierte BGR (OpenCV) a RGB. Único punto de conversión de color."""
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def build_display_image(frame, max_w: int, max_h: int):
    """Construye la imagen de presentación sin modificar el frame original.

    BGR -> RGB -> escala LANCZOS (solo presentación, nunca upscale). El
    frame de entrada no se modifica: el pipeline sigue recibiendo el frame
    real. Reutiliza el patrón probado del portable (LOOP-0017B).
    """
    src_h, src_w = frame.shape[:2]
    disp_w, disp_h = fit_display_size(src_w, src_h, max_w, max_h)
    rgb = bgr_frame_to_rgb(frame)
    image = Image.fromarray(rgb)
    if (disp_w, disp_h) != (src_w, src_h):
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
    """Select a truthful display frame, preferring exact event analytics."""
    analytics_frame = getattr(panel, "analytics_frame", None)
    analytics_frame_index = int(getattr(panel, "analytics_frame_index", -1))
    has_geometry = bool(
        tuple(getattr(panel, "bboxes", ()) or ())
        or getattr(panel, "track_bbox", None)
    )
    if analytics_frame is not None and analytics_frame_index >= 0 and has_geometry:
        return analytics_frame, analytics_frame_index, "ANALITICA"
    return getattr(panel, "frame", None), int(getattr(panel, "frame_index", -1)), "VIVO"


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

    Transición única centralizada para CAM-001..CAM-004: deriva SOLO del
    estado global/runtime (STOPPED), nunca del último metadata/frame
    retenido. Toda cámara termina gris, CLOSED, sin analytics activos.
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
    """¿Debe redibujarse el panel congelado? Por cámara, sin bandera global.

    Evita el sesgo de orden: tras STOP los cuatro paneles se redibujan en el
    primer pase aunque tamaño/índice no hayan cambiado (LOOP-0019B-R2).
    """
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

    Centro 2x2 (paneles de video grandes y dinámicos), lateral consolidado
    (seguimiento/temporal/behavior/riesgo/alertas/evidencia/clip) e
    inferior con controles claros (Detener / Abrir evidencia / Abrir clip).
    """

    POLL_MS = 33

    def __init__(self, root: tk.Tk, controller) -> None:
        self._root = root
        self._controller = controller
        self._multicamera_mode = bool(getattr(controller, "is_multicamera", False))
        self._photos = {camera_id: None for camera_id in CAMERA_IDS}
        self._last_render_index = {camera_id: -1 for camera_id in CAMERA_IDS}
        self._last_render_size = {camera_id: (0, 0) for camera_id in CAMERA_IDS}
        self._last_frame = None
        self._last_frame_index = -1
        self._evidence_btn = None
        self._clip_btn = None
        self._evidence_target: Optional[str] = None
        self._clip_target: Optional[str] = None
        self._review_available = False
        self._stopped_rendered = {camera_id: False for camera_id in CAMERA_IDS}
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        self._root.title("TukeVision - Interfaz operativa local")
        self._root.geometry("1280x720")
        self._root.minsize(1024, 640)
        self._root.configure(bg=COLORS["bg"])
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_header()
        self._build_body()
        self._build_controls()
        self._build_settings()

        self._on_source_change("FILE")
        self._root.after(self.POLL_MS, self._poll)

    def _build_header(self) -> None:
        header = tk.Frame(self._root, bg=COLORS["bg"])
        header.pack(side=tk.TOP, fill=tk.X)

        brand = tk.Frame(header, bg=COLORS["bg"])
        brand.pack(side=tk.LEFT, padx=14, pady=8)
        title_row = tk.Frame(brand, bg=COLORS["bg"])
        title_row.pack(fill=tk.X, anchor=tk.W)
        tk.Label(
            title_row, text="TUKEVISION", bg=COLORS["bg"], fg=COLORS["text"],
            font=FONT_TITLE,
        ).pack(side=tk.LEFT)
        self._live_dot = tk.Canvas(title_row, width=12, height=12, bg=COLORS["bg"],
                                   highlightthickness=0)
        self._live_dot.pack(side=tk.LEFT, padx=(10, 4), pady=2)
        self._live_label = tk.Label(
            title_row, text="IDLE", bg=COLORS["bg"], fg=COLORS["offline"],
            font=FONT_PANEL_TITLE,
        )
        self._live_label.pack(side=tk.LEFT)
        tk.Label(
            brand, text="Retail Intelligence & Loss Prevention",
            bg=COLORS["bg"], fg=COLORS["text_dim"], font=FONT_SUBTITLE,
        ).pack(fill=tk.X, anchor=tk.W)

        status = tk.Frame(header, bg=COLORS["bg"])
        status.pack(side=tk.RIGHT, padx=14, pady=8)
        self._health_var = tk.StringVar(
            value="CPU N/A | RAM N/A | DISK N/A | HEALTH UNKNOWN"
        )
        tk.Label(
            status, textvariable=self._health_var, bg=COLORS["bg"],
            fg=COLORS["text"], font=FONT_SMALL,
        ).pack(side=tk.TOP, anchor=tk.E)
        status_metrics = tk.Frame(status, bg=COLORS["bg"])
        status_metrics.pack(side=tk.TOP, anchor=tk.E)
        self._cameras_var = tk.StringVar(value="CAMERAS: 0 / 4 ONLINE")
        self._res_var = tk.StringVar(value="RES: -")
        self._fps_var = tk.StringVar(value="FPS: -")
        for var in (self._cameras_var, self._fps_var, self._res_var):
            tk.Label(
                status_metrics, textvariable=var, bg=COLORS["bg"], fg=COLORS["text_dim"],
                font=FONT_BODY,
            ).pack(side=tk.RIGHT, padx=(12, 0))

    def _build_body(self) -> None:
        body = tk.Frame(self._root, bg=COLORS["bg"])
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))
        self._build_video_area(body)
        self._build_side_panel(body)

    def _build_video_area(self, parent) -> None:
        area = tk.Frame(parent, bg=COLORS["bg"])
        area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._video_canvases = {}
        for row, columns in enumerate(PANEL_LAYOUT):
            area.rowconfigure(row, weight=1, uniform="cam")
            for column, camera_id in enumerate(columns):
                area.columnconfigure(column, weight=1, uniform="cam")
                cell = tk.Frame(
                    area, bg=COLORS["panel"],
                    highlightbackground=COLORS["border"], highlightthickness=1,
                )
                cell.grid(row=row, column=column, sticky="nsew", padx=2, pady=2)
                canvas = tk.Canvas(cell, bg="#0A0F1E", highlightthickness=0)
                canvas.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
                canvas.bind(
                    "<Configure>", lambda e, c=camera_id: self._on_canvas_resize(c)
                )
                self._video_canvases[camera_id] = canvas
                self._draw_placeholder(camera_id, canvas, "OFFLINE")

    def _build_side_panel(self, parent) -> None:
        panel = tk.Frame(parent, bg=COLORS["panel"], width=292)
        panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        panel.pack_propagate(False)
        panel.configure(highlightbackground=COLORS["border"], highlightthickness=1)

        tk.Label(
            panel, text="SEGUIMIENTO", bg=COLORS["panel"], fg=COLORS["text_dim"],
            font=FONT_PANEL_TITLE,
        ).pack(fill=tk.X, padx=10, pady=(8, 2), anchor=tk.W)
        self._cam_summary_vars = {}
        for camera_id in CAMERA_IDS:
            var = tk.StringVar(value=f"{camera_id} · OFFLINE")
            self._cam_summary_vars[camera_id] = var
            tk.Label(
                panel, textvariable=var, bg=COLORS["panel"], fg=COLORS["text"],
                font=FONT_SMALL, wraplength=262, justify=tk.LEFT,
            ).pack(fill=tk.X, padx=10, pady=1, anchor=tk.W)

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

    def _build_controls(self) -> None:
        controls = tk.Frame(self._root, bg=COLORS["bg"])
        controls.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 8))

        def button(parent, text, command, accent=False):
            return tk.Button(
                parent, text=text, command=command,
                relief=tk.FLAT, bg=COLORS["accent_dim"] if accent else COLORS["panel"],
                fg=COLORS["accent"] if accent else COLORS["text"],
                activebackground=COLORS["panel_muted"], activeforeground=COLORS["text"],
                font=FONT_BODY_BOLD, padx=14, pady=4, cursor="hand2", borderwidth=1,
                highlightbackground=COLORS["border"],
            )

        self._stop_btn = button(controls, "Detener", self._on_stop, accent=True)
        self._stop_btn.configure(state=tk.DISABLED)
        self._stop_btn.pack(side=tk.LEFT, padx=(0, 6))
        self._evidence_btn = button(controls, "Abrir evidencia", self._on_open_evidence)
        self._evidence_btn.configure(state=tk.DISABLED)
        self._evidence_btn.pack(side=tk.LEFT, padx=(0, 6))
        self._clip_btn = button(controls, "Abrir clip / revisión", self._on_open_clips)
        self._clip_btn.configure(state=tk.DISABLED)
        self._clip_btn.pack(side=tk.LEFT)

    def _build_settings(self) -> None:
        wrap = tk.Frame(self._root, bg=COLORS["bg"])
        wrap.pack(side=tk.TOP, fill=tk.X)
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
            self._stop_btn.configure(state=tk.NORMAL)

    # ------------------------------------------------------------- placeholders
    def _draw_placeholder(self, camera_id, canvas, source_state: str) -> None:
        canvas.delete("all")
        cw = max(canvas.winfo_width(), 64)
        ch = max(canvas.winfo_height(), 64)
        color = camera_status_color(source_state)
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

    # ------------------------------------------------------------- actions
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
        launcher = getattr(self._controller, "launch_review", None)
        if callable(launcher):
            launcher()
            return
        bat = Path(__file__).resolve().parents[2] / "review_behavior_signals.bat"
        if bat.is_file():
            os.startfile(str(bat))

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

    def _on_close(self) -> None:
        try:
            self._controller.close()
        finally:
            self._root.destroy()

    # ------------------------------------------------------------- poll loop
    def _poll(self) -> None:
        if not self._root.winfo_exists():
            return
        try:
            self._poll_once()
        finally:
            try:
                self._root.after(self.POLL_MS, self._poll)
            except tk.TclError:
                pass

    def _poll_once(self) -> None:
        state = self._controller.poll_state()
        if self._multicamera_mode:
            controls = multicamera_control_state(state["status"])
            self._stop_btn.configure(
                state=tk.NORMAL if controls["stop_enabled"] else tk.DISABLED
            )
        self._update_action_targets(state)
        self._render_video(state)
        self._render_header(state)
        self._render_side_panel(state)
        self._update_button_states()

    def _update_action_targets(self, state: dict) -> None:
        """Deriva los objetivos exactos de evidencia/clip desde el runtime."""
        self._evidence_target = None
        self._clip_target = None
        self._review_available = False
        if self._multicamera_mode:
            latest = getattr(self._controller, "latest_evidence", None)
            clip = getattr(self._controller, "clip_target", None)
            review = getattr(self._controller, "review_available", None)
            if callable(latest):
                self._evidence_target = latest()
            if callable(clip):
                self._clip_target = clip()
            if callable(review):
                self._review_available = bool(review())
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

    # ------------------------------------------------------------- rendering
    def _render_video(self, state: dict) -> None:
        running = state["status"] == AppStatus.RUNNING
        panels = self._controller.poll_multicamera()
        for camera_id in CAMERA_IDS:
            panel = panels[camera_id]
            canvas = self._video_canvases[camera_id]
            frame = getattr(panel, "frame", None)
            frame_index = int(getattr(panel, "frame_index", -1))
            if running:
                self._stopped_rendered[camera_id] = False
                if frame is None or frame_index < 0:
                    self._draw_placeholder(
                        camera_id, canvas,
                        str(getattr(panel, "source_state", "OFFLINE") or "OFFLINE"),
                    )
                    continue
                self._render_camera(camera_id, panel, canvas)
            else:
                stopped = apply_stopped_state(panel)
                if frame is None or frame_index < 0:
                    self._draw_placeholder(
                        camera_id, canvas, stopped["source_state"]
                    )
                    continue
                self._render_frozen_camera(
                    camera_id, canvas, frame, frame_index, stopped
                )

    def _render_camera(self, camera_id, panel, canvas) -> None:
        frame, displayed_frame_index, _ = select_panel_frame(panel)
        frame_index = int(getattr(panel, "frame_index", -1))
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        size = (cw, ch)
        changed = (
            size != self._last_render_size[camera_id]
            or frame_index != self._last_render_index[camera_id]
        )
        if not changed or cw < 32 or ch < 32:
            return
        annotated = annotate_frame(
            frame, panel, displayed_frame_index=displayed_frame_index
        )
        image = build_display_image(annotated, cw, ch)
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        try:
            photo = tk.PhotoImage(data=buf.getvalue())
        except tk.TclError:
            return
        self._photos[camera_id] = photo
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=photo, anchor=tk.CENTER)
        self._draw_overlay(canvas, camera_id, panel, cw, ch)
        self._last_render_size[camera_id] = size
        self._last_render_index[camera_id] = frame_index
        marker = getattr(self._controller, "mark_ui_rendered", None)
        if marker is not None:
            marker(camera_id, frame_index)

    def _render_frozen_camera(
        self, camera_id, canvas, frame, frame_index, stopped
    ) -> None:
        """Último frame congelado tras STOP, marcado como offline.

        Mantiene la referencia visual pero elimina todo estado activo:
        sin Track/Event/Temporal/Behavior y sin contadores verdes.
        """
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
    def _draw_overlay(canvas, camera_id, panel, cw: int, ch: int) -> None:
        state = str(getattr(panel, "source_state", "OPEN") or "OPEN")
        canvas.create_oval(6, 6, 16, 16, fill=camera_status_color(state), outline="")
        canvas.create_text(
            22, 11, anchor=tk.W, text=camera_id, fill=COLORS["text"],
            font=FONT_BODY_BOLD,
        )
        resolution = getattr(panel, "resolution", "") or ""
        if resolution:
            canvas.create_text(
                cw - 8, 11, anchor=tk.E, text=resolution,
                fill=COLORS["text_dim"], font=FONT_SMALL,
            )
        track_id = getattr(panel, "track_id", None)
        if track_id:
            canvas.create_text(
                8, ch - 12, anchor=tk.W, text=f"TRK {track_id}",
                fill="#E2A125", font=FONT_BODY_BOLD,
            )
        confidence = getattr(panel, "event_confidence", None)
        if confidence is not None:
            canvas.create_text(
                cw - 8, ch - 12, anchor=tk.E,
                text=f"{float(confidence):.0%}", fill=COLORS["text"],
                font=FONT_BODY_BOLD,
            )

    def _render_header(self, state: dict) -> None:
        running = state["status"] == AppStatus.RUNNING
        if running:
            self._set_dot(self._live_dot, COLORS["online"])
            self._live_label.configure(text="LIVE", fg=COLORS["online"])
        else:
            self._set_dot(self._live_dot, COLORS["offline"])
            self._live_label.configure(text="IDLE", fg=COLORS["offline"])
        panels = self._controller.poll_multicamera()
        health = state.get("system_health")
        self._health_var.set(health_header_text(health))
        online = (
            health.online_camera_count
            if health is not None else online_camera_count(panels, running=running)
        )
        total = health.total_camera_count if health is not None else 4
        self._cameras_var.set(f"CAMERAS: {online} / {total} ONLINE")
        resolutions = [
            str(getattr(panel, "resolution", ""))
            for panel in panels.values()
            if getattr(panel, "resolution", "")
        ]
        if resolutions:
            self._res_var.set(f"RES: {resolutions[0]}")
        fps = state.get("fps") or 0.0
        self._fps_var.set(f"FPS: {fps:.1f}" if fps else "FPS: -")

    @staticmethod
    def _set_dot(canvas, color: str) -> None:
        canvas.delete("all")
        canvas.create_oval(1, 1, 11, 11, fill=color, outline="")

    def _render_side_panel(self, state: dict) -> None:
        running = state["status"] == AppStatus.RUNNING
        panels = self._controller.poll_multicamera()
        health = state.get("system_health")
        camera_health = (
            {item.camera_id: item for item in health.camera_health}
            if health is not None else {}
        )
        for camera_id in CAMERA_IDS:
            panel = panels[camera_id]
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

    def run(self) -> None:
        self._root.mainloop()
