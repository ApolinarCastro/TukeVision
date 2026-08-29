"""Phase 12: Tkinter Operational Panels & Mode Switcher for Command Center V2.

Implements presentation frames for Operational Intelligence, 2D Spatial Map,
Agent Monitor, Evidence Selector, Governed Actions, and Health Explainability.
"""

import tkinter as tk
from tkinter import ttk
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
    GRID = "GRID"
    FOCUS = "FOCUS"
    OPERATIONAL = "OPERATIONAL"
    MAP = "MAP"
    INVESTIGATIONS = "INVESTIGATIONS"
    EVIDENCE = "EVIDENCE"
    SYSTEM = "SYSTEM"


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
        if new_mode in {
            OperationalCommandCenterModes.GRID,
            OperationalCommandCenterModes.FOCUS,
            OperationalCommandCenterModes.OPERATIONAL,
            OperationalCommandCenterModes.MAP,
            OperationalCommandCenterModes.INVESTIGATIONS,
            OperationalCommandCenterModes.EVIDENCE,
            OperationalCommandCenterModes.SYSTEM,
        }:
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
