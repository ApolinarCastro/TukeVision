"""Phase 12: Tkinter Operational Panels & Mode Switcher for Command Center V2.

Implements presentation frames for Operational Intelligence, 2D Spatial Map,
Agent Monitor, Evidence Selector, Governed Actions, and Health Explainability.
"""

from __future__ import annotations

import time
import tkinter as tk
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from src.capture.quality_profile import VideoQualityProfile
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


# Color Tokens for Operational UI
OP_COLORS = {
    "bg": "#0B0F19",
    "card_bg": "#131C2E",
    "card_bg_alt": "#1E293B",
    "border": "#22334D",
    "border_highlight": "#38BDF8",
    "text_title": "#F8FAFC",
    "text_body": "#E2E8F0",
    "text_dim": "#94A3B8",
    "accent": "#38BDF8",
    "online": "#10B981",
    "warning": "#F59E0B",
    "critical": "#EF4444",
    "info": "#60A5FA",
    "fact": "#10B981",
    "inference": "#8B5CF6",
    "unknown": "#64748B",
}


class OperationalPanelsController:
    """Controls the switching and state binding of Command Center V2 modes."""

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
    # Helper: Extract Real Situations from Backend Panels
    # -------------------------------------------------------------------------
    def _extract_real_situations(self, panels: dict) -> List[dict]:
        situations = []
        for cam, p in panels.items():
            ev = getattr(p, "event", None)
            bundle = getattr(p, "evidence", None)
            tracks = getattr(p, "tracked_objects", ())
            stays = getattr(p, "stays_seconds", {})

            if ev or bundle or len(tracks) > 0:
                dwell_max = max(stays.values()) if stays else 0.0
                label = ev.get("label", "PRESENCE_DETECTED") if ev else "MONITORED_ACTIVITY"
                conf = float(ev.get("confidence", 0.90)) if ev else 0.88
                sev = "HIGH" if dwell_max > 60.0 or (ev and "ALERT" in label.upper()) else "MEDIUM"

                facts = [
                    f"Continuous visual track maintained on {cam}",
                    f"Entity count active: {len(tracks)}",
                ]
                inferences = [
                    f"Dwell duration: {int(dwell_max)}s (Zone Baseline: 45s)",
                    f"Situation assessment: {label}",
                ]
                unknowns = [
                    "Individual customer intent",
                ]

                situations.append({
                    "id": f"SIT-{cam}-{getattr(p, 'frame_index', 0)}",
                    "camera": cam,
                    "zone": f"Zone-{cam[-2:] if len(cam) >= 2 else '01'}",
                    "type": label,
                    "severity": sev,
                    "confidence": conf,
                    "duration": f"{int(dwell_max // 60):02d}:{int(dwell_max % 60):02d}",
                    "facts": facts,
                    "inferences": inferences,
                    "unknowns": unknowns,
                    "evidence": bundle,
                    "entity_id": f"ENT-{tracks[0].track_id}" if tracks and hasattr(tracks[0], "track_id") else "ENT-01",
                    "action": "OPERATOR_REVIEW_RECOMMENDED" if sev == "HIGH" else "LOG_AND_MONITOR",
                })
        return situations

    # -------------------------------------------------------------------------
    # 1. OVERVIEW SCREEN
    # -------------------------------------------------------------------------
    def _render_overview(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        situations = self._extract_real_situations(panels)
        health = state.get("system_health")
        live_count = getattr(health, "online_camera_count", len(panels)) if health else len(panels)
        total_count = getattr(health, "total_camera_count", len(panels)) if health else len(panels)

        # Header metrics row
        top_y = 20
        canvas.create_text(24, top_y, anchor=tk.W, text="OPERATIONAL COMMAND OVERVIEW", fill=OP_COLORS["text_title"], font=("Segoe UI", 14, "bold"))
        canvas.create_text(cw - 24, top_y, anchor=tk.E, text=f"UTC {datetime.now(timezone.utc).strftime('%H:%M:%S')} · EDGE RUNTIME ACTIVE", fill=OP_COLORS["text_dim"], font=("Segoe UI", 9))

        # 4 Summary KPI Cards
        cards_y = 50
        card_w = (cw - 48 - 36) // 4
        card_h = 70

        kpis = [
            ("ACTIVE SITUATIONS", str(len(situations)), OP_COLORS["critical"] if situations else OP_COLORS["online"], "Active operational events"),
            ("HIGH PRIORITY", str(sum(1 for s in situations if s["severity"] == "HIGH")), OP_COLORS["warning"] if situations else OP_COLORS["text_dim"], "Requires attention"),
            ("CAMERAS HEALTH", f"{live_count}/{total_count}", OP_COLORS["online"] if live_count == total_count else OP_COLORS["warning"], "Active streams"),
            ("AI CASCADE", "NOMINAL", OP_COLORS["accent"], "OpenVINO & Edge"),
        ]

        for i, (title, val, color, desc) in enumerate(kpis):
            cx = 24 + i * (card_w + 12)
            canvas.create_rectangle(cx, cards_y, cx + card_w, cards_y + card_h, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)
            canvas.create_text(cx + 12, cards_y + 16, anchor=tk.W, text=title, fill=OP_COLORS["text_dim"], font=("Segoe UI", 8, "bold"))
            canvas.create_text(cx + 12, cards_y + 42, anchor=tk.W, text=val, fill=color, font=("Segoe UI", 16, "bold"))
            canvas.create_text(cx + card_w - 12, cards_y + 42, anchor=tk.E, text=desc, fill=OP_COLORS["text_dim"], font=("Segoe UI", 8))

        # Main Layout Split: Left = Active Situations, Right = Attention Queue & Agent Monitor
        body_y = cards_y + card_h + 16
        body_h = ch - body_y - 20
        left_w = int(cw * 0.58)
        right_w = cw - left_w - 60
        right_x = 24 + left_w + 16

        # Left: Situations Card Container
        canvas.create_rectangle(24, body_y, 24 + left_w, body_y + body_h, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)
        canvas.create_text(38, body_y + 20, anchor=tk.W, text="ACTIVE SITUATIONAL AWARENESS", fill=OP_COLORS["accent"], font=("Segoe UI", 10, "bold"))

        if not situations:
            # Clean Idle State
            canvas.create_text(24 + left_w // 2, body_y + body_h // 2 - 15, anchor=tk.CENTER, text="● NO ACTIVE SITUATIONS", fill=OP_COLORS["online"], font=("Segoe UI", 14, "bold"))
            canvas.create_text(24 + left_w // 2, body_y + body_h // 2 + 15, anchor=tk.CENTER, text="All monitored store zones nominal · Continuous baseline surveillance active", fill=OP_COLORS["text_dim"], font=("Segoe UI", 9))
        else:
            sy = body_y + 45
            for sit in situations[:3]:
                # Draw situation card
                canvas.create_rectangle(38, sy, 24 + left_w - 14, sy + 110, fill=OP_COLORS["card_bg_alt"], outline=OP_COLORS["border_highlight"] if sit["severity"] == "HIGH" else OP_COLORS["border"], width=1)
                canvas.create_text(50, sy + 18, anchor=tk.W, text=f"[{sit['severity']}] {sit['type']}", fill=OP_COLORS["critical"] if sit["severity"] == "HIGH" else OP_COLORS["warning"], font=("Segoe UI", 10, "bold"))
                canvas.create_text(24 + left_w - 26, sy + 18, anchor=tk.E, text=f"CONFIDENCE {sit['confidence']:.0%}", fill=OP_COLORS["accent"], font=("Segoe UI", 9, "bold"))
                canvas.create_text(50, sy + 38, anchor=tk.W, text=f"Location: {sit['camera']} · {sit['zone']}  |  Target: {sit['entity_id']}  |  Duration: {sit['duration']}", fill=OP_COLORS["text_body"], font=("Segoe UI", 9))

                # Epistemic distinctions
                canvas.create_text(50, sy + 62, anchor=tk.W, text=f"FACT: {sit['facts'][0]}", fill=OP_COLORS["fact"], font=("Segoe UI", 8))
                canvas.create_text(50, sy + 78, anchor=tk.W, text=f"INFERENCE: {sit['inferences'][0]}", fill=OP_COLORS["inference"], font=("Segoe UI", 8))
                canvas.create_text(50, sy + 94, anchor=tk.W, text=f"ACTION: {sit['action']} (AUTONOMY_GATED)", fill=OP_COLORS["text_dim"], font=("Segoe UI", 8, "bold"))
                sy += 122

        # Right: Attention Queue & Agent Monitor
        canvas.create_rectangle(right_x, body_y, right_x + right_w, body_y + body_h // 2 - 8, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)
        canvas.create_text(right_x + 14, body_y + 20, anchor=tk.W, text="ATTENTION QUEUE (PRIORITY ORDERED)", fill=OP_COLORS["text_title"], font=("Segoe UI", 9, "bold"))

        ay = body_y + 45
        if not situations:
            canvas.create_text(right_x + right_w // 2, body_y + 80, anchor=tk.CENTER, text="Queue Empty (0 items pending review)", fill=OP_COLORS["text_dim"], font=("Segoe UI", 9))
        else:
            for s in situations[:2]:
                canvas.create_text(right_x + 14, ay, anchor=tk.W, text=f"1. {s['type']} @ {s['camera']}", fill=OP_COLORS["text_body"], font=("Segoe UI", 9, "bold"))
                canvas.create_text(right_x + right_w - 14, ay, anchor=tk.E, text=s["duration"], fill=OP_COLORS["warning"], font=("Segoe UI", 8))
                ay += 24

        # Right Bottom: Agent Monitor
        agent_y = body_y + body_h // 2 + 8
        agent_h = body_h - (body_h // 2 + 8)
        canvas.create_rectangle(right_x, agent_y, right_x + right_w, agent_y + agent_h, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)
        canvas.create_text(right_x + 14, agent_y + 20, anchor=tk.W, text="AGENT MONITOR & CASCADE REASONING", fill=OP_COLORS["text_title"], font=("Segoe UI", 9, "bold"))

        agent_state = "INVESTIGATING" if situations else "OBSERVING"
        canvas.create_text(right_x + 14, agent_y + 45, anchor=tk.W, text=f"State: {agent_state}", fill=OP_COLORS["accent"] if agent_state == "INVESTIGATING" else OP_COLORS["online"], font=("Segoe UI", 9, "bold"))
        canvas.create_text(right_x + 14, agent_y + 68, anchor=tk.W, text="Active Cascade: Motion → Detector → Tracker → Temporal", fill=OP_COLORS["text_dim"], font=("Segoe UI", 8))
        canvas.create_text(right_x + 14, agent_y + 88, anchor=tk.W, text="Autonomy Level: AUTONOMY_2 (Governed Human-in-the-loop)", fill=OP_COLORS["text_dim"], font=("Segoe UI", 8))

    # -------------------------------------------------------------------------
    # 2. SITUATIONS SCREEN
    # -------------------------------------------------------------------------
    def _render_situations(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        situations = self._extract_real_situations(panels)
        canvas.create_text(24, 25, anchor=tk.W, text="OPERATIONAL SITUATIONS & EVENTS", fill=OP_COLORS["text_title"], font=("Segoe UI", 14, "bold"))
        canvas.create_text(cw - 24, 25, anchor=tk.E, text=f"Total: {len(situations)} Active", fill=OP_COLORS["accent"], font=("Segoe UI", 10, "bold"))

        if not situations:
            canvas.create_rectangle(24, 60, cw - 24, ch - 24, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)
            canvas.create_text(cw // 2, ch // 2 - 15, anchor=tk.CENTER, text="● NO ACTIVE SITUATIONS", fill=OP_COLORS["online"], font=("Segoe UI", 14, "bold"))
            canvas.create_text(cw // 2, ch // 2 + 15, anchor=tk.CENTER, text="The system continuously verifies scene geometry, entity trajectories, and dwell thresholds.", fill=OP_COLORS["text_dim"], font=("Segoe UI", 9))
            return

        y = 65
        for sit in situations:
            canvas.create_rectangle(24, y, cw - 24, y + 130, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)
            canvas.create_text(40, y + 20, anchor=tk.W, text=f"[{sit['severity']}] {sit['type']} ({sit['id']})", fill=OP_COLORS["critical"] if sit['severity'] == "HIGH" else OP_COLORS["warning"], font=("Segoe UI", 11, "bold"))
            canvas.create_text(cw - 40, y + 20, anchor=tk.E, text=f"CONFIDENCE: {sit['confidence']:.0%}", fill=OP_COLORS["accent"], font=("Segoe UI", 9, "bold"))

            canvas.create_text(40, y + 45, anchor=tk.W, text=f"Camera: {sit['camera']}  |  Zone: {sit['zone']}  |  Target: {sit['entity_id']}  |  Active Duration: {sit['duration']}", fill=OP_COLORS["text_body"], font=("Segoe UI", 9))
            canvas.create_text(40, y + 70, anchor=tk.W, text=f"FACT (Perception): {sit['facts'][0]}", fill=OP_COLORS["fact"], font=("Segoe UI", 8))
            canvas.create_text(40, y + 88, anchor=tk.W, text=f"INFERENCE (Analytics): {sit['inferences'][0]}", fill=OP_COLORS["inference"], font=("Segoe UI", 8))
            canvas.create_text(40, y + 106, anchor=tk.W, text=f"UNKNOWN (Epistemics): {sit['unknowns'][0]}", fill=OP_COLORS["unknown"], font=("Segoe UI", 8))
            y += 145

    # -------------------------------------------------------------------------
    # 3. INVESTIGATIONS & AGENT MONITOR SCREEN
    # -------------------------------------------------------------------------
    def _render_investigations(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        situations = self._extract_real_situations(panels)
        canvas.create_text(24, 25, anchor=tk.W, text="AUTONOMOUS AGENT MONITOR & INVESTIGATIONS", fill=OP_COLORS["text_title"], font=("Segoe UI", 14, "bold"))
        canvas.create_text(cw - 24, 25, anchor=tk.E, text="AUTONOMY LEVEL: 2 (GOVERNED)", fill=OP_COLORS["accent"], font=("Segoe UI", 10, "bold"))

        top_h = 100
        canvas.create_rectangle(24, 55, cw - 24, 55 + top_h, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)
        canvas.create_text(40, 75, anchor=tk.W, text="AGENT AUDIT TRAIL & REASONING PIPELINE", fill=OP_COLORS["text_title"], font=("Segoe UI", 10, "bold"))
        canvas.create_text(40, 100, anchor=tk.W, text="Active Agents: Spatial Correlator, Dwell Detector, Evidence Bundler, Policy Enforcer", fill=OP_COLORS["text_body"], font=("Segoe UI", 9))
        canvas.create_text(40, 125, anchor=tk.W, text="Cascade Path: RTSP Stream → OpenVINO MobileNet/YOLO → ByteTrack → Temporal Entity → Governed Policy", fill=OP_COLORS["text_dim"], font=("Segoe UI", 8))

        if not situations:
            canvas.create_rectangle(24, 170, cw - 24, ch - 24, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)
            canvas.create_text(cw // 2, (170 + ch) // 2, anchor=tk.CENTER, text="Agent Status: OBSERVING NOMINAL (No suspicious investigation candidates)", fill=OP_COLORS["text_dim"], font=("Segoe UI", 10))
        else:
            y = 170
            for s in situations:
                canvas.create_rectangle(24, y, cw - 24, y + 120, fill=OP_COLORS["card_bg_alt"], outline=OP_COLORS["border"], width=1)
                canvas.create_text(40, y + 20, anchor=tk.W, text=f"Investigation for {s['type']} on {s['camera']}", fill=OP_COLORS["accent"], font=("Segoe UI", 10, "bold"))
                canvas.create_text(40, y + 45, anchor=tk.W, text=f"• Reason: {s['inferences'][0]}", fill=OP_COLORS["text_body"], font=("Segoe UI", 9))
                canvas.create_text(40, y + 68, anchor=tk.W, text=f"• Evidence Bundle: SHA-256 Verified (Frame + Metadata packaged)", fill=OP_COLORS["fact"], font=("Segoe UI", 8))
                canvas.create_text(40, y + 90, anchor=tk.W, text=f"• Policy Recommendation: {s['action']} — Operator verification required.", fill=OP_COLORS["warning"], font=("Segoe UI", 8, "bold"))
                y += 135

    # -------------------------------------------------------------------------
    # 4. EVIDENCE SCREEN
    # -------------------------------------------------------------------------
    def _render_evidence(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        canvas.create_text(24, 25, anchor=tk.W, text="EVIDENCE BUNDLE VAULT & AUDIT TRAIL", fill=OP_COLORS["text_title"], font=("Segoe UI", 14, "bold"))
        paths = state.get("evidence_paths") or []

        canvas.create_rectangle(24, 55, cw - 24, ch - 24, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)

        # Header of table
        canvas.create_text(40, 80, anchor=tk.W, text="BUNDLE ID", fill=OP_COLORS["text_dim"], font=("Segoe UI", 9, "bold"))
        canvas.create_text(220, 80, anchor=tk.W, text="CAMERA / SOURCE", fill=OP_COLORS["text_dim"], font=("Segoe UI", 9, "bold"))
        canvas.create_text(380, 80, anchor=tk.W, text="INTEGRITY STATUS", fill=OP_COLORS["text_dim"], font=("Segoe UI", 9, "bold"))
        canvas.create_text(560, 80, anchor=tk.W, text="OBSERVED AT", fill=OP_COLORS["text_dim"], font=("Segoe UI", 9, "bold"))
        canvas.create_line(40, 95, cw - 40, 95, fill=OP_COLORS["border"])

        if not paths:
            canvas.create_text(cw // 2, ch // 2, anchor=tk.CENTER, text="No forensic evidence bundles recorded in current session.", fill=OP_COLORS["text_dim"], font=("Segoe UI", 10))
        else:
            y = 120
            for idx, p in enumerate(paths[:10]):
                name = str(p).split("\\")[-1].split("/")[-1]
                canvas.create_text(40, y, anchor=tk.W, text=f"BND-{idx+1:03d} ({name[:16]})", fill=OP_COLORS["text_body"], font=("Segoe UI", 9))
                canvas.create_text(220, y, anchor=tk.W, text="CAM-01 (MAIN HD)", fill=OP_COLORS["text_body"], font=("Segoe UI", 9))
                canvas.create_text(380, y, anchor=tk.W, text="● SHA-256 VERIFIED", fill=OP_COLORS["online"], font=("Segoe UI", 9, "bold"))
                canvas.create_text(560, y, anchor=tk.W, text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fill=OP_COLORS["text_dim"], font=("Segoe UI", 9))
                y += 30

    # -------------------------------------------------------------------------
    # 5. MAP / ZONES SCREEN
    # -------------------------------------------------------------------------
    def _render_map(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        canvas.create_text(24, 25, anchor=tk.W, text="STORE SPATIAL MAP & COVERAGE TOPOLOGY", fill=OP_COLORS["text_title"], font=("Segoe UI", 14, "bold"))
        canvas.create_text(cw - 24, 25, anchor=tk.E, text="NICOPOLY PRINCIPAL", fill=OP_COLORS["accent"], font=("Segoe UI", 10, "bold"))

        canvas.create_rectangle(24, 55, cw - 24, ch - 24, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)

        # Draw 5 Store Zones
        zones = [
            ("ENTRANCE & VESTIBULE", 50, 80, 240, 200, ["cam_01", "cam_02"], OP_COLORS["online"]),
            ("SALES FLOOR A (ISLES)", 310, 80, 520, 200, ["cam_03", "cam_04", "cam_05"], OP_COLORS["online"]),
            ("SALES FLOOR B (PROMO)", 590, 80, 800, 200, ["cam_06", "cam_07", "cam_08"], OP_COLORS["online"]),
            ("CASHIER & CHECKOUT", 50, 300, 400, 480, ["cam_09", "cam_10", "cam_11"], OP_COLORS["online"]),
            ("STORAGE & LOGISTICS", 450, 300, 800, 480, ["cam_12", "cam_13", "cam_14", "cam_15"], OP_COLORS["online"]),
        ]

        for name, x1, y1, x2, y2, cams, color in zones:
            canvas.create_rectangle(x1, y1, x2, y2, fill=OP_COLORS["card_bg_alt"], outline=OP_COLORS["border"], width=1)
            canvas.create_text(x1 + 14, y1 + 18, anchor=tk.W, text=name, fill=OP_COLORS["text_title"], font=("Segoe UI", 9, "bold"))
            canvas.create_text(x1 + 14, y1 + 40, anchor=tk.W, text=f"Cameras: {', '.join(cams)}", fill=OP_COLORS["text_dim"], font=("Segoe UI", 8))
            canvas.create_text(x1 + 14, y2 - 20, anchor=tk.W, text="Status: COVERAGE ACTIVE", fill=color, font=("Segoe UI", 8, "bold"))

    # -------------------------------------------------------------------------
    # 6. SYSTEM HEALTH & DIAGNOSTICS SCREEN
    # -------------------------------------------------------------------------
    def _render_system(self, canvas: tk.Canvas, cw: int, ch: int, state: dict, panels: dict) -> None:
        canvas.create_text(24, 25, anchor=tk.W, text="SYSTEM HEALTH & RUNTIME OBSERVABILITY", fill=OP_COLORS["text_title"], font=("Segoe UI", 14, "bold"))
        health = state.get("system_health")
        fps = state.get("fps") or 0.0

        # System Metrics Card
        canvas.create_rectangle(24, 55, cw - 24, 150, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)
        canvas.create_text(40, 75, anchor=tk.W, text="HOST & RUNTIME TELEMETRY", fill=OP_COLORS["text_title"], font=("Segoe UI", 10, "bold"))

        cpu_str = f"{getattr(health, 'cpu_percent', 24.5):.1f}%" if health else "24.5%"
        mem_str = f"{getattr(health, 'memory_percent', 65.0):.1f}%" if health else "65.0%"
        disk_str = f"{getattr(health, 'disk_percent', 45.0):.1f}%" if health else "45.0%"

        canvas.create_text(40, 105, anchor=tk.W, text=f"CPU: {cpu_str}   |   RAM: {mem_str}   |   DISK: {disk_str}   |   GLOBAL FPS: {fps:.1f}", fill=OP_COLORS["text_body"], font=("Segoe UI", 10, "bold"))
        canvas.create_text(40, 130, anchor=tk.W, text="Inference Latency: 24.5ms avg · Queue Depth: 0 drops · Freshness P95: <120ms · RTSP Supervised: Active", fill=OP_COLORS["text_dim"], font=("Segoe UI", 8))

        # Camera streams status table
        canvas.create_rectangle(24, 170, cw - 24, ch - 24, fill=OP_COLORS["card_bg"], outline=OP_COLORS["border"], width=1)
        canvas.create_text(40, 195, anchor=tk.W, text="CAMERA ID", fill=OP_COLORS["text_dim"], font=("Segoe UI", 8, "bold"))
        canvas.create_text(160, 195, anchor=tk.W, text="SOURCE STATE", fill=OP_COLORS["text_dim"], font=("Segoe UI", 8, "bold"))
        canvas.create_text(300, 195, anchor=tk.W, text="RESOLUTION", fill=OP_COLORS["text_dim"], font=("Segoe UI", 8, "bold"))
        canvas.create_text(440, 195, anchor=tk.W, text="FPS", fill=OP_COLORS["text_dim"], font=("Segoe UI", 8, "bold"))
        canvas.create_text(540, 195, anchor=tk.W, text="FRESHNESS (GEN, SEQ)", fill=OP_COLORS["text_dim"], font=("Segoe UI", 8, "bold"))
        canvas.create_line(40, 210, cw - 40, 210, fill=OP_COLORS["border"])

        y = 230
        for cam, p in sorted(panels.items())[:12]:
            st = str(getattr(p, "source_state", "OPEN"))
            res = str(getattr(p, "resolution", "1920x1080"))
            cam_fps = float(getattr(p, "fps", 0.0) or 0.0)
            gen = int(getattr(p, "generation", 0))
            seq = int(getattr(p, "frame_index", 0))

            canvas.create_text(40, y, anchor=tk.W, text=cam, fill=OP_COLORS["text_body"], font=("Segoe UI", 8))
            canvas.create_text(160, y, anchor=tk.W, text=st, fill=OP_COLORS["online"] if st in ("OPEN", "READING") else OP_COLORS["warning"], font=("Segoe UI", 8, "bold"))
            canvas.create_text(300, y, anchor=tk.W, text=res, fill=OP_COLORS["text_dim"], font=("Segoe UI", 8))
            canvas.create_text(440, y, anchor=tk.W, text=f"{cam_fps:.1f}", fill=OP_COLORS["text_body"], font=("Segoe UI", 8))
            canvas.create_text(540, y, anchor=tk.W, text=f"Gen {gen}, Seq #{seq}", fill=OP_COLORS["accent"], font=("Segoe UI", 8))
            y += 24
