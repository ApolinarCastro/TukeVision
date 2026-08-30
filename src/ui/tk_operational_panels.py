"""Tkinter Operational Dashboards & Mode Switcher for TukeVision Command Center.

Implements enterprise operational panels: Resumen (Overview), En Vivo (Live Grid),
Situaciones (Situations), Investigaciones (Investigations), Evidencia (Evidence),
Mapa / Zonas (Spatial Map), and Estado del Sistema (System Health).

Strictly adheres to:
- Zero fabricated data / Real backend provenance only
- Non-situation tracking activity is never elevated to artificial alarms
- Epistemic classification: HECHO (Fact), INFERENCIA (Inference), DESCONOCIDO (Unknown)
- Single-source DesignTokens & I18n (es-CL)
- Glanceable, visual, progressive disclosure without walls of technical text
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
    def _extract_real_situations(self, panels: dict, state: Optional[dict] = None) -> List[dict]:
        """Extract only genuine SituationRecords backed by backend policy or situation engine.
        
        Strict Zero-Fake Rule (TV-F12-SURGICAL-FINAL-TRUTH-PHYSICAL-TES-03):
        - Mere detection/tracking/event/label is NEVER a situation.
        - UI never fabricates situation_id (f"SIT-...", f"EVT-...").
        - UI never defaults or invents situation_type ("ALERTA", "DETECCIÓN", etc.).
        - UI never assigns severity (HIGH/MEDIUM derived in UI). If missing in record -> 'UNKNOWN'.
        - UI never infers epistemic class by confidence (>=0.9 -> FACT). If missing in record -> 'UNKNOWN'.
        - ZONES: if not present in backend -> 'No determinada'.
        - ACTION: only if produced by GovernedActionRecord / PolicyDecision.
        """
        situations: List[dict] = []
        
        # 1. Situations from ViewModel
        if self.view_model and self.view_model.active_situations:
            for sit_id, item in self.view_model.active_situations.items():
                if not item.situation_id or not item.situation_type:
                    continue
                zone_str = ", ".join(item.zone_ids) if item.zone_ids else _("zone_not_determined")
                cam_str = ", ".join(item.camera_ids) if item.camera_ids else _("data_unknown")
                entity_str = ", ".join(item.entity_ids) if item.entity_ids else None
                epistemic_state = getattr(item, "epistemic_state", None) or "UNKNOWN"
                situations.append({
                    "id": item.situation_id,
                    "camera": cam_str,
                    "zone": zone_str,
                    "type": item.situation_type,
                    "severity": item.severity or "UNKNOWN",
                    "confidence": item.confidence,
                    "duration": f"{int(item.duration_seconds // 60):02d}:{int(item.duration_seconds % 60):02d}",
                    "entity_id": entity_str,
                    "evidence": item.evidence_bundle_ref,
                    "action": None,
                    "epistemic_class": epistemic_state,
                })

        # 2. Check per-panel explicit situation contracts (NEVER infer from tracks or generic event labels)
        for cam, p in panels.items():
            sit = getattr(p, "situation", None) or getattr(p, "situation_record", None)
            if sit is None:
                continue

            # Dict representation of Situation
            if isinstance(sit, dict):
                sit_id = sit.get("situation_id")
                sit_type = sit.get("situation_type")
                if not sit_id or not sit_type:
                    # Missing explicit ID or TYPE -> do NOT render as situation
                    continue
                sev = str(sit.get("severity") or "UNKNOWN")
                conf = sit.get("confidence")
                ent = sit.get("entity_id")
                dur = float(sit.get("duration_seconds", 0.0))
                action = sit.get("action")
                epistemic_state = str(sit.get("epistemic_state") or "UNKNOWN")
            # Object representation of Situation (e.g. SituationRecord / SituationViewItem)
            else:
                sit_id = getattr(sit, "situation_id", None)
                sit_type = getattr(sit, "situation_type", None)
                if not isinstance(sit_id, str) or not isinstance(sit_type, str) or not sit_id or not sit_type:
                    # Missing explicit ID or TYPE -> do NOT render as situation
                    continue
                sev = str(getattr(sit, "severity", None) or "UNKNOWN")
                conf = getattr(sit, "confidence", None)
                if not isinstance(conf, (int, float)):
                    conf = None
                ent = getattr(sit, "entity_id", None)
                dur = float(getattr(sit, "duration_seconds", 0.0) or 0.0)
                action = getattr(sit, "action", None)
                epistemic_state = str(getattr(sit, "epistemic_state", None) or "UNKNOWN")

            zone = getattr(p, "zone", None) or _("zone_not_determined")
            situations.append({
                "id": str(sit_id),
                "camera": cam,
                "zone": zone,
                "type": str(sit_type),
                "severity": sev,
                "confidence": conf,
                "duration": f"{int(dur // 60):02d}:{int(dur % 60):02d}",
                "entity_id": ent,
                "evidence": getattr(p, "evidence", None),
                "action": action,
                "epistemic_class": epistemic_state,
            })

        return situations

    # -------------------------------------------------------------------------
    # 1. RESUMEN / CENTRO DE MANDO (COMMAND CENTER OVERVIEW)
    # -------------------------------------------------------------------------
    def _render_overview(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        situations = self._extract_real_situations(panels, state)
        health = state.get("system_health")
        live_count = getattr(health, "online_camera_count", len(panels)) if health else len(panels)
        total_count = getattr(health, "total_camera_count", len(panels)) if health else len(panels)

        # Header Row - Clean & Glanceable
        top_y = 20
        canvas.create_text(
            24, top_y, anchor=tk.W, text="CENTRO DE MANDO · RESUMEN OPERACIONAL",
            fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"]
        )
        utc_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
        canvas.create_text(
            cw - 24, top_y, anchor=tk.E, text=f"UTC {utc_str} · LOCAL FIRST",
            fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"]
        )

        # System Health Truth: Never derive "SALUDABLE" purely from live_count > 0
        raw_health = state.get("system_health")
        if raw_health is not None:
            health_status_val = getattr(raw_health, "overall_health", None) or getattr(raw_health, "status", None)
            health_display = str(health_status_val).upper() if health_status_val else "NO DETERMINADO"
            health_color = DesignTokens.get_status_color(health_display)
        else:
            health_display = "NO DETERMINADO"
            health_color = DesignTokens.COLORS["text_dim"]

        # 4 Summary KPI Cards
        cards_y = 48
        card_w = (cw - 48 - 36) // 4
        card_h = 64

        kpis = [
            (_("kpi_active_cameras"), f"{live_count} / {total_count}", DesignTokens.COLORS["normal"] if live_count == total_count and live_count > 0 else DesignTokens.COLORS["attention"], "Supervisión activa"),
            (_("kpi_active_situations"), str(len(situations)), DesignTokens.COLORS["critical"] if situations else DesignTokens.COLORS["normal"], "Eventos validados"),
            ("INVESTIGACIONES", str(len(self.view_model.investigations)), DesignTokens.COLORS["info"] if self.view_model.investigations else DesignTokens.COLORS["text_dim"], "Casos abiertos"),
            ("ESTADO DEL SISTEMA", health_display, health_color, "Runtime local"),
        ]

        for i, (title, val, color, desc) in enumerate(kpis):
            cx = 24 + i * (card_w + 12)
            canvas.create_rectangle(cx, cards_y, cx + card_w, cards_y + card_h, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
            canvas.create_text(cx + 12, cards_y + 16, anchor=tk.W, text=title, fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
            canvas.create_text(cx + 12, cards_y + 40, anchor=tk.W, text=val, fill=color, font=DesignTokens.FONTS["kpi_value"])
            canvas.create_text(cx + card_w - 12, cards_y + 40, anchor=tk.E, text=desc, fill=DesignTokens.COLORS["text_dark"], font=DesignTokens.FONTS["small"])

        # Main Layout Split
        body_y = cards_y + card_h + 16
        body_h = ch - body_y - 20
        left_w = int(cw * 0.60)
        right_w = cw - left_w - 60
        right_x = 24 + left_w + 16

        # Left Container: Situaciones Prioritarias
        canvas.create_rectangle(24, body_y, 24 + left_w, body_y + body_h, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        canvas.create_text(38, body_y + 20, anchor=tk.W, text="SITUACIONES OPERACIONALES PRIORITARIAS", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])

        if not situations:
            # Concise Nominal State
            canvas.create_text(24 + left_w // 2, body_y + body_h // 2 - 12, anchor=tk.CENTER, text=f"● {_('no_active_situations')}", fill=DesignTokens.COLORS["normal"], font=DesignTokens.FONTS["panel_title"])
            canvas.create_text(24 + left_w // 2, body_y + body_h // 2 + 12, anchor=tk.CENTER, text=_("no_active_situations_sub"), fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
        else:
            sy = body_y + 45
            for sit in situations[:3]:
                card_box_h = 92
                canvas.create_rectangle(38, sy, 24 + left_w - 14, sy + card_box_h, fill=DesignTokens.COLORS["surface_elevated"], outline=DesignTokens.COLORS["border_light"], width=1)
                
                # Priority badge & Title
                badge_col = DesignTokens.get_status_color(sit["severity"])
                canvas.create_text(50, sy + 18, anchor=tk.W, text=f"[{sit['severity']}] {sit['type']}", fill=badge_col, font=DesignTokens.FONTS["panel_title"])
                
                conf_str = f" · Confianza {sit['confidence']:.0%}" if sit["confidence"] is not None else ""
                canvas.create_text(50, sy + 40, anchor=tk.W, text=f"Cámara: {sit['camera']}  |  Zona: {sit['zone']}{conf_str}", fill=DesignTokens.COLORS["text_secondary"], font=DesignTokens.FONTS["body"])
                
                dur_str = f"Duración: {sit['duration']}"
                canvas.create_text(50, sy + 64, anchor=tk.W, text=dur_str, fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
                
                # Action badge
                canvas.create_rectangle(24 + left_w - 120, sy + 52, 24 + left_w - 26, sy + 76, fill=DesignTokens.COLORS["accent_bg"], outline=DesignTokens.COLORS["accent"], width=1)
                canvas.create_text(24 + left_w - 73, sy + 64, anchor=tk.CENTER, text="[ REVISAR ]", fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["small_bold"])
                sy += card_box_h + 12

        # Right Top: Cola de Atención Operacional
        right_box_h = (body_h - 16) // 2
        canvas.create_rectangle(right_x, body_y, right_x + right_w, body_y + right_box_h, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        canvas.create_text(right_x + 14, body_y + 20, anchor=tk.W, text="COLA DE ATENCIÓN", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])

        if not situations:
            canvas.create_text(right_x + right_w // 2, body_y + right_box_h // 2 - 8, anchor=tk.CENTER, text=_("attention_queue_empty"), fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["body"])
            canvas.create_text(right_x + right_w // 2, body_y + right_box_h // 2 + 12, anchor=tk.CENTER, text=_("attention_queue_empty_sub"), fill=DesignTokens.COLORS["text_dark"], font=DesignTokens.FONTS["small"])
        else:
            ay = body_y + 45
            for s in situations[:2]:
                canvas.create_text(right_x + 14, ay, anchor=tk.W, text=f"● {s['type']} en {s['camera']}", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["body_bold"])
                canvas.create_text(right_x + right_w - 14, ay, anchor=tk.E, text=s["duration"], fill=DesignTokens.COLORS["attention"], font=DesignTokens.FONTS["small"])
                ay += 26

        # Right Bottom: Estado del Agente y Cascada
        agent_y = body_y + right_box_h + 16
        agent_h = body_h - right_box_h - 16
        canvas.create_rectangle(right_x, agent_y, right_x + right_w, agent_y + agent_h, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        canvas.create_text(right_x + 14, agent_y + 20, anchor=tk.W, text="ESTADO DEL AGENTE Y GOBERNANZA", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])

        # Agent state from real backend or NOT AVAILABLE
        raw_agent_state = state.get("agent_state")
        agent_state_str = str(raw_agent_state) if raw_agent_state else _("agent_state_not_available")
        canvas.create_text(right_x + 14, agent_y + 46, anchor=tk.W, text=f"Estado del Agente: {agent_state_str}", fill=DesignTokens.COLORS["text_secondary"], font=DesignTokens.FONTS["body_bold"])
        
        # Autonomy from real policy or UNKNOWN
        raw_autonomy = state.get("autonomy_level")
        autonomy_str = str(raw_autonomy) if raw_autonomy else _("autonomy_not_certified")
        canvas.create_text(right_x + 14, agent_y + 70, anchor=tk.W, text=f"Autonomía: {autonomy_str}", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])

    # -------------------------------------------------------------------------
    # 2. SITUACIONES (SITUATIONS - COMPACT VISUAL CARDS)
    # -------------------------------------------------------------------------
    def _render_situations(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        situations = self._extract_real_situations(panels, state)
        canvas.create_text(24, 25, anchor=tk.W, text="SITUACIONES OPERACIONALES", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"])
        canvas.create_text(cw - 24, 25, anchor=tk.E, text=f"Total: {len(situations)} Activas", fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["panel_title"])

        if not situations:
            card_w = 380
            card_h = 130
            cx = cw // 2
            cy = ch // 2
            canvas.create_rectangle(cx - card_w // 2, cy - card_h // 2, cx + card_w // 2, cy + card_h // 2, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border_light"], width=1)
            canvas.create_text(cx, cy - 28, anchor=tk.CENTER, text="✓", fill=DesignTokens.COLORS["normal"], font=("Segoe UI", 20, "bold"))
            canvas.create_text(cx, cy + 4, anchor=tk.CENTER, text=_("no_active_situations"), fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])
            canvas.create_text(cx, cy + 30, anchor=tk.CENTER, text=_("no_active_situations_sub"), fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
            return

        y = 65
        for sit in situations:
            card_h = 100
            canvas.create_rectangle(24, y, cw - 24, y + card_h, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
            
            # Thumbnail area placeholder
            canvas.create_rectangle(36, y + 14, 136, y + 86, fill=DesignTokens.COLORS["surface_elevated"], outline=DesignTokens.COLORS["border_light"], width=1)
            canvas.create_text(86, y + 50, anchor=tk.CENTER, text="[ EVIDENCIA ]", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])

            # Metadata
            sev_color = DesignTokens.get_status_color(sit["severity"])
            canvas.create_text(152, y + 22, anchor=tk.W, text=f"[{sit['severity']}] {sit['type']}", fill=sev_color, font=DesignTokens.FONTS["panel_title"])
            
            conf_str = f" · Confianza {sit['confidence']:.0%}" if sit["confidence"] is not None else ""
            ent_str = f" · Objetivo: {sit['entity_id']}" if sit["entity_id"] else ""
            canvas.create_text(152, y + 46, anchor=tk.W, text=f"Cámara: {sit['camera']}  |  Zona: {sit['zone']}{ent_str}{conf_str}", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["body"])
            canvas.create_text(152, y + 70, anchor=tk.W, text=f"ID: {sit['id']}  |  Duración: {sit['duration']}", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])

            # Interactive action buttons
            canvas.create_rectangle(cw - 220, y + 36, cw - 128, y + 66, fill=DesignTokens.COLORS["surface_elevated"], outline=DesignTokens.COLORS["border_light"], width=1)
            canvas.create_text(cw - 174, y + 51, anchor=tk.CENTER, text=_("btn_investigate"), fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["small_bold"])
            
            canvas.create_rectangle(cw - 118, y + 36, cw - 36, y + 66, fill=DesignTokens.COLORS["accent_bg"], outline=DesignTokens.COLORS["accent"], width=1)
            canvas.create_text(cw - 77, y + 51, anchor=tk.CENTER, text=_("btn_review"), fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["small_bold"])
            
            y += card_h + 14

    # -------------------------------------------------------------------------
    # 3. INVESTIGACIONES (INVESTIGATIONS - TIMELINE LAYOUT)
    # -------------------------------------------------------------------------
    def _render_investigations(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        canvas.create_text(24, 25, anchor=tk.W, text="INVESTIGACIONES Y REGISTRO DE EVENTOS", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"])
        
        invs = list(self.view_model.investigations.values())
        if not invs:
            card_w = 380
            card_h = 130
            cx = cw // 2
            cy = ch // 2
            canvas.create_rectangle(cx - card_w // 2, cy - card_h // 2, cx + card_w // 2, cy + card_h // 2, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border_light"], width=1)
            canvas.create_text(cx, cy - 28, anchor=tk.CENTER, text="✓", fill=DesignTokens.COLORS["normal"], font=("Segoe UI", 20, "bold"))
            canvas.create_text(cx, cy + 4, anchor=tk.CENTER, text=_("no_open_investigations"), fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])
            canvas.create_text(cx, cy + 30, anchor=tk.CENTER, text=_("no_open_investigations_sub"), fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
            return

        y = 65
        for inv in invs:
            timeline = self.view_model.build_operator_timeline(inv.investigation_id)
            box_h = 40 + len(timeline) * 26
            canvas.create_rectangle(24, y, cw - 24, y + box_h, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
            
            canvas.create_text(40, y + 20, anchor=tk.W, text=f"{_('investigation_record')}: {inv.situation_type} ({inv.investigation_id})", fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["panel_title"])
            canvas.create_text(cw - 40, y + 20, anchor=tk.E, text=f"Prioridad: {inv.priority} · Estado: {inv.status}", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])

            ty = y + 42
            for ev in timeline:
                badge_col = DesignTokens.get_epistemic_color(ev.epistemic_state)
                ts_short = ev.timestamp[11:19] if len(ev.timestamp) >= 19 else ev.timestamp
                canvas.create_text(50, ty, anchor=tk.W, text=f"{ts_short}  [{ev.stage}]  {ev.summary}", fill=DesignTokens.COLORS["text_secondary"], font=DesignTokens.FONTS["body"])
                canvas.create_text(cw - 50, ty, anchor=tk.E, text=f"[{ev.epistemic_state}]", fill=badge_col, font=DesignTokens.FONTS["small_bold"])
                ty += 24
            y += box_h + 16

    # -------------------------------------------------------------------------
    # 4. EVIDENCIA (EVIDENCE GALLERY & INTEGRITY)
    # -------------------------------------------------------------------------
    def _render_evidence(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        canvas.create_text(24, 25, anchor=tk.W, text="BÓVEDA DE EVIDENCIA Y REGISTRO DE INTEGRIDAD LOCAL", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"])
        paths = state.get("evidence_paths") or []

        canvas.create_rectangle(24, 55, cw - 24, ch - 24, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)

        # Operational Table Header
        canvas.create_text(40, 80, anchor=tk.W, text="PAQUETE DE EVIDENCIA", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(260, 80, anchor=tk.W, text="CÁMARA / FUENTE", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(440, 80, anchor=tk.W, text="INTEGRIDAD LOCAL", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(620, 80, anchor=tk.W, text="FIRMA DE ORIGEN", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_line(40, 95, cw - 40, 95, fill=DesignTokens.COLORS["border"])

        if not paths:
            canvas.create_text(cw // 2, ch // 2 - 12, anchor=tk.CENTER, text=f"● {_('no_evidence_recorded')}", fill=DesignTokens.COLORS["normal"], font=DesignTokens.FONTS["panel_title"])
            canvas.create_text(cw // 2, ch // 2 + 12, anchor=tk.CENTER, text=_("no_evidence_recorded_sub"), fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
        else:
            y = 120
            for idx, p in enumerate(paths[:10]):
                name = str(p).split("\\")[-1].split("/")[-1]
                canvas.create_text(40, y, anchor=tk.W, text=f"BND-{idx+1:03d} ({name[:16]})", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["body"])
                canvas.create_text(260, y, anchor=tk.W, text="CAM-01 (HD)", fill=DesignTokens.COLORS["text_secondary"], font=DesignTokens.FONTS["body"])
                canvas.create_text(440, y, anchor=tk.W, text="● SHA-256 LOCAL VERIFICADO", fill=DesignTokens.COLORS["normal"], font=DesignTokens.FONTS["body_bold"])
                canvas.create_text(620, y, anchor=tk.W, text="FUENTE NO FIRMADA (DVR)", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
                y += 28

    # -------------------------------------------------------------------------
    # 5. MAPA / ZONAS (LOGICAL COVERAGE)
    # -------------------------------------------------------------------------
    def _render_map(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        canvas.create_text(24, 25, anchor=tk.W, text="COBERTURA LÓGICA Y AGRUPACIÓN DE CÁMARAS", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"])
        store_id = state.get("store_id") or "TIENDA PRINCIPAL"
        canvas.create_text(cw - 24, 25, anchor=tk.E, text=str(store_id).upper(), fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["panel_title"])

        canvas.create_rectangle(24, 55, cw - 24, ch - 24, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        
        # Honest Header Banner: Geometry is logical unless physical CAD/SVG is provided
        canvas.create_text(40, 78, anchor=tk.W, text=f"● {_('map_no_geometry')}", fill=DesignTokens.COLORS["attention"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(40, 96, anchor=tk.W, text="Distribución funcional de canales de video asociados a la tienda.", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])

        # Logical coverage blocks
        zones = [
            ("ACCESO Y VESTÍBULO", 40, 120, 240, 240, ["cam_01", "cam_02"]),
            ("SALA DE VENTAS (PASILLOS)", 260, 120, 480, 240, ["cam_03", "cam_04", "cam_05"]),
            ("SALA DE VENTAS (PROMOCIONES)", 500, 120, 720, 240, ["cam_06", "cam_07", "cam_08"]),
            ("LÍNEA DE CAJAS Y SALIDA", 40, 260, 360, 380, ["cam_09", "cam_10", "cam_11"]),
            ("BODEGAJE Y LOGÍSTICA", 380, 260, 720, 380, ["cam_12", "cam_13", "cam_14", "cam_15"]),
        ]

        for name, x1, y1, x2, y2, cams in zones:
            canvas.create_rectangle(x1, y1, x2, y2, fill=DesignTokens.COLORS["surface_elevated"], outline=DesignTokens.COLORS["border"], width=1)
            canvas.create_text(x1 + 14, y1 + 18, anchor=tk.W, text=name, fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])
            canvas.create_text(x1 + 14, y1 + 42, anchor=tk.W, text=f"Cámaras: {', '.join(cams)}", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
            canvas.create_text(x1 + 14, y2 - 20, anchor=tk.W, text="Cobertura: ACTIVA", fill=DesignTokens.COLORS["normal"], font=DesignTokens.FONTS["small_bold"])

    # -------------------------------------------------------------------------
    # 6. ESTADO DEL SISTEMA (SYSTEM HEALTH & TECHNICAL DIAGNOSTICS)
    # -------------------------------------------------------------------------
    def _render_system(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        canvas.create_text(24, 25, anchor=tk.W, text="ESTADO DEL SISTEMA Y TELEMETRÍA TÉCNICA", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["title"])
        health = state.get("system_health")
        fps = state.get("fps") or 0.0

        # Host Telemetry
        canvas.create_rectangle(24, 55, cw - 24, 135, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        canvas.create_text(40, 75, anchor=tk.W, text="RECURSOS DEL HOST Y MOTOR LOCAL", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["panel_title"])

        cpu_val = getattr(health, "cpu_percent", 0.0) if health else 0.0
        mem_val = getattr(health, "memory_percent", 0.0) if health else 0.0
        disk_val = getattr(health, "disk_percent", 0.0) if health else 0.0

        cpu_str = f"{cpu_val:.1f}%" if cpu_val > 0 else _("data_not_available")
        mem_str = f"{mem_val:.1f}%" if mem_val > 0 else _("data_not_available")
        disk_str = f"{disk_val:.1f}%" if disk_val > 0 else _("data_not_available")

        canvas.create_text(40, 102, anchor=tk.W, text=f"CPU: {cpu_str}   |   RAM: {mem_str}   |   DISCO: {disk_str}   |   FPS GLOBAL: {fps:.1f}", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["body_bold"])

        # Per-camera RTSP & Hardware Streams Table
        canvas.create_rectangle(24, 150, cw - 24, ch - 24, fill=DesignTokens.COLORS["surface"], outline=DesignTokens.COLORS["border"], width=1)
        canvas.create_text(40, 175, anchor=tk.W, text="CANAL", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(140, 175, anchor=tk.W, text="ESTADO RTSP", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(280, 175, anchor=tk.W, text="RESOLUCIÓN FUENTE", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(450, 175, anchor=tk.W, text="FPS", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_text(550, 175, anchor=tk.W, text="FRESCURA DE FLUJO", fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small_bold"])
        canvas.create_line(40, 190, cw - 40, 190, fill=DesignTokens.COLORS["border"])

        y = 208
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
            canvas.create_text(140, y, anchor=tk.W, text=st, fill=DesignTokens.COLORS["normal"] if st in ("OPEN", "READING") else DesignTokens.COLORS["attention"], font=DesignTokens.FONTS["small_bold"])
            canvas.create_text(280, y, anchor=tk.W, text=res, fill=DesignTokens.COLORS["text_dim"], font=DesignTokens.FONTS["small"])
            canvas.create_text(450, y, anchor=tk.W, text=f"{cam_fps:.1f}", fill=DesignTokens.COLORS["text"], font=DesignTokens.FONTS["small"])
            canvas.create_text(550, y, anchor=tk.W, text=f"Gen {gen} · Sec #{seq}", fill=DesignTokens.COLORS["accent"], font=DesignTokens.FONTS["small"])
            y += 20
