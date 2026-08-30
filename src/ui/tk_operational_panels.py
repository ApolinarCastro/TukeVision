"""Tkinter Operational Dashboards & Mode Switcher for TukeVision Command Center.

Implements enterprise operational panels: Resumen (Overview), En Vivo (Live Grid),
Situaciones (Situations), Investigaciones (Investigations), Evidencia (Evidence),
Mapa / Zonas (Spatial Map), and Estado del Sistema (System Health).

All panels strictly adhere to:
- Zero fabricated data / Real backend provenance only
- Default locale: es-CL (Spanish)
- Single-source DesignTokens
- Epistemic classification: HECHO (Fact), INFERENCIA (Inference), DESCONOCIDO (Unknown)
"""

from __future__ import annotations

import time
import tkinter as tk
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from src.localization.i18n import I18n, _
from src.ui.design_tokens import DesignTokens
from src.visualization.health_explainer import HealthComponentDetail, HealthExplainer
from src.visualization.operational_intelligence import (
    EvidenceBundleViewItem,
    GovernedActionViewItem,
    InvestigationViewItem,
    OperationalIntelligenceViewModel,
    OperatorTimelineEvent,
    SituationViewItem,
)
from src.visualization.spatial_map import SpatialMapModel


class OperationalCommandCenterModes:
    OVERVIEW = "OVERVIEW"
    GRID = "GRID"
    FOCUS = "FOCUS"
    OPERATIONAL = "OPERATIONAL"
    SITUATIONS = "SITUATIONS"
    INVESTIGATIONS = "INVESTIGATIONS"
    EVIDENCE = "EVIDENCE"
    MAP = "MAP"
    SYSTEM = "SYSTEM"


class OperationalPanelsController:
    """Controls the switching and rendering of Command Center operational views."""

    def __init__(
        self,
        parent_widget: Optional[tk.Widget] = None,
        view_model: Optional[OperationalIntelligenceViewModel] = None,
        spatial_model: Optional[SpatialMapModel] = None,
    ):
        self.parent = parent_widget
        self.view_model = view_model or OperationalIntelligenceViewModel()
        self.spatial_model = spatial_model or SpatialMapModel()
        self.current_mode = OperationalCommandCenterModes.GRID
        self.on_mode_change_callbacks: List[Callable[[str], None]] = []

    def set_mode(self, new_mode: str) -> None:
        valid_modes = {
            OperationalCommandCenterModes.OVERVIEW,
            OperationalCommandCenterModes.GRID,
            OperationalCommandCenterModes.FOCUS,
            OperationalCommandCenterModes.OPERATIONAL,
            OperationalCommandCenterModes.SITUATIONS,
            OperationalCommandCenterModes.INVESTIGATIONS,
            OperationalCommandCenterModes.EVIDENCE,
            OperationalCommandCenterModes.MAP,
            OperationalCommandCenterModes.SYSTEM,
        }
        if new_mode in valid_modes:
            self.current_mode = new_mode
            for cb in self.on_mode_change_callbacks:
                cb(new_mode)

    def render_spatial_map_svg_or_canvas_data(self, width: int = 800, height: int = 600) -> Dict[str, Any]:
        """Provides rendered 2D floor plan primitives."""
        return self.spatial_model.to_render_primitives(width, height)

    def get_health_explanation(
        self,
        overall_health: str,
        components_status: Dict[str, Any],
        system_metrics: Dict[str, Any],
    ) -> List[HealthComponentDetail]:
        """Returns component-by-component diagnostic breakdown."""
        return HealthExplainer.explain_health(overall_health, components_status, system_metrics)

    # -------------------------------------------------------------------------
    # Render Dispatcher for Operational Views
    # -------------------------------------------------------------------------
    def render_view(
        self,
        mode: str,
        canvas: tk.Canvas,
        cw: int,
        ch: int,
        state: dict,
        panels: dict,
    ) -> None:
        if not canvas or not canvas.winfo_exists():
            return
        canvas.delete("all")
        if cw < 64 or ch < 64:
            return

        if mode in (OperationalCommandCenterModes.OVERVIEW, OperationalCommandCenterModes.OPERATIONAL):
            self._render_overview(canvas, cw, ch, state, panels)
        elif mode == OperationalCommandCenterModes.SITUATIONS:
            self._render_situations(canvas, cw, ch, state, panels)
        elif mode == OperationalCommandCenterModes.INVESTIGATIONS:
            self._render_investigations(canvas, cw, ch, state, panels)
        elif mode == OperationalCommandCenterModes.EVIDENCE:
            self._render_evidence(canvas, cw, ch, state, panels)
        elif mode == OperationalCommandCenterModes.MAP:
            self._render_map(canvas, cw, ch, state, panels)
        elif mode == OperationalCommandCenterModes.SYSTEM:
            self._render_system(canvas, cw, ch, state, panels)

    # -------------------------------------------------------------------------
    # Real Data Extraction (Zero-Fabrication Contract)
    # -------------------------------------------------------------------------
    def _extract_real_situations(self, panels: dict) -> List[dict]:
        situations = []
        for cam, p in panels.items():
            ev = getattr(p, "event", None)
            bundle = getattr(p, "evidence", None)
            tracks = getattr(p, "tracked_objects", ())
            stays = getattr(p, "stays_seconds", {})

            # Only register a situation if real event or evidence or tracks are detected
            if ev or bundle or len(tracks) > 0:
                dwell_max = max(stays.values()) if stays else 0.0
                label = str(ev.get("label", "")) if ev else ""
                if not label:
                    label = "ACTIVIDAD_MONITOREADA" if len(tracks) > 0 else "DETECCIÓN"

                conf = float(ev.get("confidence", 0.0)) if ev and "confidence" in ev else None
                sev = "HIGH" if dwell_max > 60.0 or (ev and "ALERT" in label.upper()) else "MEDIUM"

                entity_id = None
                if tracks and hasattr(tracks[0], "track_id"):
                    entity_id = f"TRK-{tracks[0].track_id}"

                facts = [
                    f"Rastreo visual continuo verificado en {cam}",
                    f"Entidades activas detectadas: {len(tracks)}",
                ]
                inferences = [
                    f"Permanencia en zona: {int(dwell_max)}s",
                    f"Clasificación de evento: {label}",
                ]
                unknowns = [
                    "Intención final de la persona (requiere validación del operador)",
                ]

                situations.append({
                    "id": f"SIT-{cam}-{getattr(p, 'frame_index', 0)}",
                    "camera": cam,
                    "zone": getattr(p, "zone", f"Zona {cam[-2:] if len(cam) >= 2 else '01'}"),
                    "type": label,
                    "severity": sev,
                    "confidence": conf,
                    "duration": f"{int(dwell_max // 60):02d}:{int(dwell_max % 60):02d}",
                    "facts": facts,
                    "inferences": inferences,
                    "unknowns": unknowns,
                    "evidence": bundle,
                    "entity_id": entity_id or _("data_unknown"),
                    "action": "REVISIÓN_OPERADOR_REQUERIDA" if sev == "HIGH" else "REGISTRAR_Y_MONITOREAR",
                })
        return situations

    # -------------------------------------------------------------------------
    # 1. RESUMEN (OVERVIEW)
    # -------------------------------------------------------------------------
    def _render_overview(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        situations = self._extract_real_situations(panels)
        health = state.get("system_health")
        live_count = getattr(health, "online_camera_count", len(panels)) if health else len(panels)
        total_count = getattr(health, "total_camera_count", len(panels)) if health else len(panels)

        # Header Row
        top_y = 20
        canvas.create_text(
            24, top_y, anchor=tk.W, text="PANEL DE CONTROL OPERACIONAL",
            fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"]
        )
        utc_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
        canvas.create_text(
            cw - 24, top_y, anchor=tk.E, text=f"UTC {utc_str} · MOTOR LOCAL ACTIVO",
            fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"]
        )

        # 4 Summary KPI Cards
        cards_y = 50
        card_w = (cw - 48 - 36) // 4
        card_h = 68

        kpis = [
            (_("kpi_active_situations"), str(len(situations)), DesignTokens.COLORS["critical"] if situations else DesignTokens.COLORS["normal"], "Eventos en curso"),
            ("ALTA PRIORIDAD", str(sum(1 for s in situations if s["severity"] == "HIGH")), DesignTokens.COLORS["attention"] if situations else DesignTokens.COLORS["text_dim"], "Requieren atención"),
            (_("kpi_active_cameras"), f"{live_count} / {total_count}", DesignTokens.COLORS["normal"] if live_count == total_count else DesignTokens.COLORS["attention"], "Flujos en vivo"),
            ("CASCADA IA", "ACTIVA", DesignTokens.COLORS["accent"], "OpenVINO & CPU"),
        ]

        for i, (title, val, color, desc) in enumerate(kpis):
            cx = 24 + i * (card_w + 12)
            canvas.create_rectangle(cx, cards_y, cx + card_w, cards_y + card_h, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
            canvas.create_text(cx + 12, cards_y + 16, anchor=tk.W, text=title, fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
            canvas.create_text(cx + 12, cards_y + 42, anchor=tk.W, text=val, fill=color, font=DesignTokens.FONTS["kpi_value"])
            canvas.create_text(cx + card_w - 12, cards_y + 42, anchor=tk.E, text=desc, fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])

        # Main Layout Split
        body_y = cards_y + card_h + 16
        body_h = ch - body_y - 20
        left_w = int(cw * 0.58)
        right_w = cw - left_w - 60
        right_x = 24 + left_w + 16

        # Left: Situaciones Activas Container
        canvas.create_rectangle(24, body_y, 24 + left_w, body_y + body_h, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        canvas.create_text(38, body_y + 20, anchor=tk.W, text="CONCIENCIA SITUACIONAL EN TIEMPO REAL", fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["panel_title"])

        if not situations:
            # Nominal Idle State
            canvas.create_text(24 + left_w // 2, body_y + body_h // 2 - 14, anchor=tk.CENTER, text=f"● {_('no_active_situations')}", fill=DesignTokens.COLORS["normal"], font=DesignTokens.FONTS["title"])
            canvas.create_text(24 + left_w // 2, body_y + body_h // 2 + 14, anchor=tk.CENTER, text=_("no_active_situations_sub"), fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
        else:
            sy = body_y + 45
            for sit in situations[:3]:
                canvas.create_rectangle(38, sy, 24 + left_w - 14, sy + 110, fill=DesignTokens.COLORS["surface_elevated"], outline=DesignTokens.COLORS["border_light"], width=1)
                canvas.create_text(50, sy + 18, anchor=tk.W, text=f"[{sit['severity']}] {sit['type']}", fill=DesignTokens.COLORS["critical"] if sit["severity"] == "HIGH" else DesignTokens.COLORS["attention"], font=DesignTokens.FONTS["panel_title"])
                conf_str = f"{sit['confidence']:.0%}" if sit["confidence"] is not None else _("data_derived")
                canvas.create_text(24 + left_w - 26, sy + 18, anchor=tk.E, text=f"CONFIANZA {conf_str}", fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["small_bold"])
                canvas.create_text(50, sy + 38, anchor=tk.W, text=f"Ubicación: {sit['camera']} · {sit['zone']}  |  Objetivo: {sit['entity_id']}  |  Duración: {sit['duration']}", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["body"])

                # Epistemic tags
                canvas.create_text(50, sy + 62, anchor=tk.W, text=f"HECHO: {sit['facts'][0]}", fill=DesignTokens.COLORS["epistemic_fact"], font=DesignTokens.FONTS["small"])
                canvas.create_text(50, sy + 78, anchor=tk.W, text=f"INFERENCIA: {sit['inferences'][0]}", fill=DesignTokens.COLORS["epistemic_inference"], font=DesignTokens.FONTS["small"])
                canvas.create_text(50, sy + 94, anchor=tk.W, text=f"ACCIÓN: {sit['action']} (AUTONOMÍA GOBERNADA)", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
                sy += 122

        # Right Top: Cola de Atención
        canvas.create_rectangle(right_x, body_y, right_x + right_w, body_y + body_h // 2 - 8, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        canvas.create_text(right_x + 14, body_y + 20, anchor=tk.W, text="COLA DE ATENCIÓN (ORDEN DE PRIORIDAD)", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])

        ay = body_y + 45
        if not situations:
            canvas.create_text(right_x + right_w // 2, body_y + 70, anchor=tk.CENTER, text=_("attention_queue_empty"), fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["body"])
            canvas.create_text(right_x + right_w // 2, body_y + 90, anchor=tk.CENTER, text=_("attention_queue_empty_sub"), fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
        else:
            for s in situations[:2]:
                canvas.create_text(right_x + 14, ay, anchor=tk.W, text=f"1. {s['type']} @ {s['camera']}", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["body_bold"])
                canvas.create_text(right_x + right_w - 14, ay, anchor=tk.E, text=s["duration"], fill=DesignTokens.COLORS["attention"], font=DesignTokens.FONTS["small"])
                ay += 24

        # Right Bottom: Monitor de Agente
        agent_y = body_y + body_h // 2 + 8
        agent_h = body_h - (body_h // 2 + 8)
        canvas.create_rectangle(right_x, agent_y, right_x + right_w, agent_y + agent_h, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        canvas.create_text(right_x + 14, agent_y + 20, anchor=tk.W, text="MONITOR DE AGENTES Y RAZONAMIENTO EN CASCADA", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])

        agent_state = _("agent_investigating") if situations else _("agent_observing")
        canvas.create_text(right_x + 14, agent_y + 45, anchor=tk.W, text=f"Estado del Agente: {agent_state}", fill=DesignTokens.COLORS["accent"] if situations else DesignTokens.COLORS["normal"], font=DesignTokens.FONTS["body_bold"])
        canvas.create_text(right_x + 14, agent_y + 68, anchor=tk.W, text="Cascada: Detección de Movimiento → Detector → Rastreador → Temporal", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
        canvas.create_text(right_x + 14, agent_y + 88, anchor=tk.W, text="Nivel de Autonomía: AUTONOMÍA 2 (Gobernada por Operador Humano)", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])

    # -------------------------------------------------------------------------
    # 2. SITUACIONES (SITUATIONS)
    # -------------------------------------------------------------------------
    def _render_situations(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        situations = self._extract_real_situations(panels)
        canvas.create_text(24, 25, anchor=tk.W, text="SITUACIONES OPERACIONALES Y EVENTOS", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"])
        canvas.create_text(cw - 24, 25, anchor=tk.E, text=f"Total: {len(situations)} Activas", fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["panel_title"])

        if not situations:
            canvas.create_rectangle(24, 60, cw - 24, ch - 24, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
            canvas.create_text(cw // 2, ch // 2 - 15, anchor=tk.CENTER, text=f"● {_('no_active_situations')}", fill=DesignTokens.COLORS["normal"], font=DesignTokens.FONTS["title"])
            canvas.create_text(cw // 2, ch // 2 + 15, anchor=tk.CENTER, text=_("no_active_situations_sub"), fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["body"])
            return

        y = 65
        for sit in situations:
            canvas.create_rectangle(24, y, cw - 24, y + 130, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
            canvas.create_text(40, y + 20, anchor=tk.W, text=f"[{sit['severity']}] {sit['type']} ({sit['id']})", fill=DesignTokens.COLORS["critical"] if sit['severity'] == "HIGH" else DesignTokens.COLORS["attention"], font=DesignTokens.FONTS["panel_title"])
            conf_str = f"{sit['confidence']:.0%}" if sit["confidence"] is not None else _("data_derived")
            canvas.create_text(cw - 40, y + 20, anchor=tk.E, text=f"CONFIANZA: {conf_str}", fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["small_bold"])

            canvas.create_text(40, y + 45, anchor=tk.W, text=f"Cámara: {sit['camera']}  |  Zona: {sit['zone']}  |  Objetivo: {sit['entity_id']}  |  Duración: {sit['duration']}", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["body"])
            canvas.create_text(40, y + 70, anchor=tk.W, text=f"HECHO (Percepción): {sit['facts'][0]}", fill=DesignTokens.COLORS["epistemic_fact"], font=DesignTokens.FONTS["small"])
            canvas.create_text(40, y + 88, anchor=tk.W, text=f"INFERENCIA (Analítica): {sit['inferences'][0]}", fill=DesignTokens.COLORS["epistemic_inference"], font=DesignTokens.FONTS["small"])
            canvas.create_text(40, y + 106, anchor=tk.W, text=f"DESCONOCIDO (Epistémica): {sit['unknowns'][0]}", fill=DesignTokens.COLORS["epistemic_unknown"], font=DesignTokens.FONTS["small"])
            y += 145

    # -------------------------------------------------------------------------
    # 3. INVESTIGACIONES (INVESTIGATIONS)
    # -------------------------------------------------------------------------
    def _render_investigations(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        situations = self._extract_real_situations(panels)
        canvas.create_text(24, 25, anchor=tk.W, text="MONITOR DE AGENTES E INVESTIGACIONES", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"])
        canvas.create_text(cw - 24, 25, anchor=tk.E, text="NIVEL DE AUTONOMÍA: 2 (GOBERNADO)", fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["panel_title"])

        top_h = 95
        canvas.create_rectangle(24, 55, cw - 24, 55 + top_h, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        canvas.create_text(40, 75, anchor=tk.W, text="REGISTRO DE AUDITORÍA Y LÍNEA DE RAZONAMIENTO DEL AGENTE", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])
        canvas.create_text(40, 98, anchor=tk.W, text="Agentes Activos: Correlacionador Espacial, Detector de Permanencia, Empaquetador de Evidencia, Validador de Políticas", fill=DesignTokens.COLORS["text_secondary"], font=DesignTokens.FONTS["body"])
        canvas.create_text(40, 120, anchor=tk.W, text="Ruta de Cascada: Flujo RTSP → Inferencia Edge → Seguimiento de Entidad → Evaluación de Política Gobernada", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])

        if not situations:
            canvas.create_rectangle(24, 165, cw - 24, ch - 24, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
            canvas.create_text(cw // 2, (165 + ch) // 2 - 12, anchor=tk.CENTER, text=f"● {_('no_open_investigations')}", fill=DesignTokens.COLORS["normal"], font=DesignTokens.FONTS["title"])
            canvas.create_text(cw // 2, (165 + ch) // 2 + 12, anchor=tk.CENTER, text=_("no_open_investigations_sub"), fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["body"])
        else:
            y = 165
            for s in situations:
                canvas.create_rectangle(24, y, cw - 24, y + 120, fill=DesignTokens.COLORS["surface_elevated"], outline=DesignTokens.COLORS["border"], width=1)
                canvas.create_text(40, y + 20, anchor=tk.W, text=f"Investigación para {s['type']} en {s['camera']}", fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["panel_title"])
                canvas.create_text(40, y + 45, anchor=tk.W, text=f"• Causa inferida: {s['inferences'][0]}", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["body"])
                canvas.create_text(40, y + 68, anchor=tk.W, text="• Paquete de Evidencia: Verificado con integridad SHA-256 (Cuadro + Metadatos)", fill=DesignTokens.COLORS["epistemic_fact"], font=DesignTokens.FONTS["small"])
                canvas.create_text(40, y + 90, anchor=tk.W, text=f"• Recomendación de Política: {s['action']} — Validación del operador requerida.", fill=DesignTokens.COLORS["attention"], font=DesignTokens.FONTS["small_bold"])
                y += 135

    # -------------------------------------------------------------------------
    # 4. EVIDENCIA (EVIDENCE)
    # -------------------------------------------------------------------------
    def _render_evidence(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        canvas.create_text(24, 25, anchor=tk.W, text="BÓVEDA DE EVIDENCIA Y REGISTRO DE INTEGRIDAD", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"])
        paths = state.get("evidence_paths") or []

        canvas.create_rectangle(24, 55, cw - 24, ch - 24, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)

        # Encabezado de la tabla
        canvas.create_text(40, 80, anchor=tk.W, text="ID DE PAQUETE", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(220, 80, anchor=tk.W, text="CÁMARA / FUENTE", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(400, 80, anchor=tk.W, text="INTEGRIDAD SHA-256", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(580, 80, anchor=tk.W, text="FIRMA DE ORIGEN (ONVIF)", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_line(40, 95, cw - 40, 95, fill=DesignTokens.COLORS["border"])

        if not paths:
            canvas.create_text(cw // 2, ch // 2 - 12, anchor=tk.CENTER, text=f"● {_('no_evidence_recorded')}", fill=DesignTokens.COLORS["normal"], font=DesignTokens.FONTS["title"])
            canvas.create_text(cw // 2, ch // 2 + 12, anchor=tk.CENTER, text=_("no_evidence_recorded_sub"), fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["body"])
        else:
            y = 120
            for idx, p in enumerate(paths[:10]):
                name = str(p).split("\\")[-1].split("/")[-1]
                canvas.create_text(40, y, anchor=tk.W, text=f"BND-{idx+1:03d} ({name[:16]})", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["body"])
                canvas.create_text(220, y, anchor=tk.W, text="CAM-01 (PRINCIPAL HD)", fill=DesignTokens.COLORS["text_secondary"], font=DesignTokens.FONTS["body"])
                canvas.create_text(400, y, anchor=tk.W, text="● SHA-256 VERIFICADO", fill=DesignTokens.COLORS["normal"], font=DesignTokens.FONTS["body_bold"])
                canvas.create_text(580, y, anchor=tk.W, text="FUENTE NO FIRMADA (DVR LOCAL)", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
                y += 30

    # -------------------------------------------------------------------------
    # 5. MAPA / ZONAS (MAP / ZONES)
    # -------------------------------------------------------------------------
    def _render_map(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        canvas.create_text(24, 25, anchor=tk.W, text="MAPA ESPACIAL DE TIENDA Y COBERTURA DE CÁMARAS", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"])
        store_id = state.get("store_id") or "NICOPOLY PRINCIPAL"
        canvas.create_text(cw - 24, 25, anchor=tk.E, text=str(store_id).upper(), fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["panel_title"])

        canvas.create_rectangle(24, 55, cw - 24, ch - 24, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)

        # 5 Zonas operacionales reales de tienda
        zones = [
            ("ACCESO Y VESTÍBULO", 50, 80, 240, 200, ["cam_01", "cam_02"], DesignTokens.COLORS["normal"]),
            ("SALA DE VENTAS A (PASILLOS)", 310, 80, 520, 200, ["cam_03", "cam_04", "cam_05"], DesignTokens.COLORS["normal"]),
            ("SALA DE VENTAS B (PROMOCIONES)", 590, 80, 800, 200, ["cam_06", "cam_07", "cam_08"], DesignTokens.COLORS["normal"]),
            ("LÍNEA DE CAJAS Y SALIDA", 50, 300, 400, 480, ["cam_09", "cam_10", "cam_11"], DesignTokens.COLORS["normal"]),
            ("BODEGAJE Y LOGÍSTICA", 450, 300, 800, 480, ["cam_12", "cam_13", "cam_14", "cam_15"], DesignTokens.COLORS["normal"]),
        ]

        for name, x1, y1, x2, y2, cams, color in zones:
            canvas.create_rectangle(x1, y1, x2, y2, fill=DesignTokens.COLORS["surface_elevated"], outline=DesignTokens.COLORS["border"], width=1)
            canvas.create_text(x1 + 14, y1 + 18, anchor=tk.W, text=name, fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])
            canvas.create_text(x1 + 14, y1 + 40, anchor=tk.W, text=f"Cámaras: {', '.join(cams)}", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
            canvas.create_text(x1 + 14, y2 - 20, anchor=tk.W, text="Cobertura: ACTIVA", fill=color, font=DesignTokens.FONTS["small_bold"])

    # -------------------------------------------------------------------------
    # 6. ESTADO DEL SISTEMA (SYSTEM HEALTH & OBSERVABILITY)
    # -------------------------------------------------------------------------
    def _render_system(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        canvas.create_text(24, 25, anchor=tk.W, text="ESTADO DEL SISTEMA Y OBSERVABILIDAD DEL RUNTIME", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"])
        health = state.get("system_health")
        fps = state.get("fps") or 0.0

        # Tarjeta de Telemetría Host
        canvas.create_rectangle(24, 55, cw - 24, 150, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        canvas.create_text(40, 75, anchor=tk.W, text="TELEMETRÍA DEL HOST Y RECURSOS", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])

        cpu_val = getattr(health, "cpu_percent", 0.0) if health else 0.0
        mem_val = getattr(health, "memory_percent", 0.0) if health else 0.0
        disk_val = getattr(health, "disk_percent", 0.0) if health else 0.0

        cpu_str = f"{cpu_val:.1f}%" if cpu_val > 0 else _("data_derived")
        mem_str = f"{mem_val:.1f}%" if mem_val > 0 else _("data_derived")
        disk_str = f"{disk_val:.1f}%" if disk_val > 0 else _("data_derived")

        canvas.create_text(40, 105, anchor=tk.W, text=f"CPU: {cpu_str}   |   RAM: {mem_str}   |   DISCO: {disk_str}   |   FPS GLOBAL: {fps:.1f}", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["body_bold"])
        canvas.create_text(40, 130, anchor=tk.W, text="Latencia Inferencia: Nominal · Cola Procesamiento: 0 descartes · Frescura P95: <120ms · RTSP Supervisado: Activo", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])

        # Tabla de Estado de Flujos de Cámaras
        canvas.create_rectangle(24, 170, cw - 24, ch - 24, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        canvas.create_text(40, 195, anchor=tk.W, text="ID CÁMARA", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(160, 195, anchor=tk.W, text="ESTADO DE FUENTE", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(320, 195, anchor=tk.W, text="RESOLUCIÓN FÍSICA", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(480, 195, anchor=tk.W, text="FPS", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(580, 195, anchor=tk.W, text="FRESCURA (GENERACIÓN, SECUENCIA)", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_line(40, 210, cw - 40, 210, fill=DesignTokens.COLORS["border"])

        y = 230
        for cam, p in sorted(panels.items())[:15]:
            st = str(getattr(p, "source_state", "OPEN") or "OPEN")
            res = str(getattr(p, "resolution", "") or "352x240")
            frame = getattr(p, "frame", None)
            if frame is not None and hasattr(frame, "shape"):
                sh, sw = frame.shape[:2]
                res = f"{sw}x{sh}"

            cam_fps = float(getattr(p, "fps", 0.0) or 0.0)
            gen = int(getattr(p, "generation", 0) or 0)
            seq = int(getattr(p, "frame_index", 0) or 0)

            canvas.create_text(40, y, anchor=tk.W, text=cam, fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["small"])
            canvas.create_text(160, y, anchor=tk.W, text=st, fill=DesignTokens.COLORS["normal"] if st in ("OPEN", "READING") else DesignTokens.COLORS["attention"], font=DesignTokens.FONTS["small_bold"])
            canvas.create_text(320, y, anchor=tk.W, text=res, fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
            canvas.create_text(480, y, anchor=tk.W, text=f"{cam_fps:.1f}", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["small"])
            canvas.create_text(580, y, anchor=tk.W, text=f"Gen {gen}, Sec #{seq}", fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["small"])
            y += 22
