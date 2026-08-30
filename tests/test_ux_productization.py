"""Targeted Unit Tests for UX Productization, DesignTokens, and Zero-Fake Governance (es-CL)."""

import tkinter as tk
import unittest
from unittest import mock

from tests.conftest import shared_root
from src.localization.i18n import DEFAULT_LOCALE, I18n, _
from src.ui.design_tokens import DesignTokens
from src.ui.tk_operational_panels import (
    OperationalCommandCenterModes,
    OperationalPanelsController,
)
from src.ui.tk_view import TkApp
from src.visualization.operational_intelligence import (
    OperationalIntelligenceViewModel,
    SituationViewItem,
)


class TestUXProductization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = shared_root()

    def setUp(self):
        I18n.set_locale("es-CL")
        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except tk.TclError:
                pass

    def test_default_locale_is_es_cl(self):
        self.assertEqual(DEFAULT_LOCALE, "es-CL")
        self.assertEqual(I18n.get_locale(), "es-CL")

    def test_core_translations_in_spanish(self):
        self.assertEqual(_("tab_overview"), "📊 RESUMEN")
        self.assertEqual(_("tab_grid"), "📹 EN VIVO")
        self.assertEqual(_("tab_situations"), "⚠️ SITUACIONES")
        self.assertEqual(_("tab_investigations"), "🔍 INVESTIGACIONES")
        self.assertEqual(_("tab_evidence"), "📁 EVIDENCIA")
        self.assertEqual(_("tab_map"), "🗺️ MAPA / ZONAS")
        self.assertEqual(_("tab_system"), "⚙️ ESTADO DEL SISTEMA")
        self.assertEqual(_("no_active_situations"), "SIN SITUACIONES ACTIVAS")
        self.assertEqual(_("attention_queue_empty"), "COLA DE ATENCIÓN VACÍA")
        self.assertEqual(_("epistemic_fact"), "HECHO")
        self.assertEqual(_("epistemic_inference"), "INFERENCIA")
        self.assertEqual(_("epistemic_unknown"), "DESCONOCIDO")

    def test_design_tokens_single_source(self):
        self.assertIn("bg", DesignTokens.COLORS)
        self.assertIn("surface", DesignTokens.COLORS)
        self.assertIn("accent", DesignTokens.COLORS)
        self.assertIn("normal", DesignTokens.COLORS)
        self.assertIn("attention", DesignTokens.COLORS)
        self.assertIn("critical", DesignTokens.COLORS)

        self.assertEqual(DesignTokens.get_status_color("ONLINE"), DesignTokens.COLORS["normal"])
        self.assertEqual(DesignTokens.get_status_color("DEGRADED"), DesignTokens.COLORS["attention"])
        self.assertEqual(DesignTokens.get_status_color("CRITICAL"), DesignTokens.COLORS["critical"])
        self.assertEqual(DesignTokens.get_epistemic_color("FACT"), DesignTokens.COLORS["epistemic_fact"])
        self.assertEqual(DesignTokens.get_epistemic_color("INFERENCE"), DesignTokens.COLORS["epistemic_inference"])

    def test_operational_panels_nominal_empty_state_zero_fake_data(self):
        controller = OperationalPanelsController()
        canvas = tk.Canvas(self.root, width=800, height=600)
        canvas.pack()
        self.root.update_idletasks()

        # Pass empty panels -> Must render nominal empty state with zero fake data
        controller.render_view(
            OperationalCommandCenterModes.OVERVIEW,
            canvas,
            800,
            600,
            {"status": "IDLE"},
            {},
        )
        all_text = [canvas.itemcget(item, "text") for item in canvas.find_all() if canvas.type(item) == "text"]
        self.assertTrue(any("SIN SITUACIONES ACTIVAS" in t for t in all_text))
        self.assertTrue(any("COLA DE ATENCIÓN VACÍA" in t for t in all_text))

    def test_focus_hd_hud_spanish_labels(self):
        canvas = tk.Canvas(self.root, width=640, height=480)
        canvas.pack()
        self.root.update_idletasks()

        panel_mock = mock.MagicMock()
        panel_mock.resolution = "1920x1080"
        panel_mock.source_state = "OPEN"
        panel_mock.frame = None

        TkApp._draw_overlay(
            canvas, "cam_01", panel_mock, 640, 480, health_state="ONLINE", focus=True
        )
        all_text = [canvas.itemcget(item, "text") for item in canvas.find_all() if canvas.type(item) == "text"]
        self.assertTrue(any("FUENTE: 1920x1080" in t for t in all_text))
        self.assertTrue(any("PRESENTACIÓN: 640x480" in t for t in all_text))
        self.assertTrue(any("PERFIL: PRINCIPAL (HD)" in t for t in all_text))

    # -------------------------------------------------------------------------
    # Negative Tests (Zero Fake Intelligence Gate)
    # -------------------------------------------------------------------------
    def test_tracks_alone_do_not_create_situations(self):
        """Detection / Track != Situation: mere tracks must NEVER produce a fake situation."""
        controller = OperationalPanelsController()
        panel_mock = mock.MagicMock()
        panel_mock.tracked_objects = [mock.MagicMock(track_id=42)]
        panel_mock.stays_seconds = {42: 120.0}
        panel_mock.situation = None
        panel_mock.situation_record = None
        panel_mock.event = None
        panel_mock.evidence = None

        situations = controller._extract_real_situations({"cam_01": panel_mock})
        self.assertEqual(len(situations), 0, "Tracking data must NOT be elevated to fake situation")

    def test_genuine_situation_record_is_rendered(self):
        """Genuine SituationRecord from backend IS properly extracted."""
        controller = OperationalPanelsController()
        panel_mock = mock.MagicMock()
        panel_mock.situation = mock.MagicMock(
            situation_id="SIT-001",
            situation_type="PERMANENCIA_PROLONGADA",
            severity="HIGH",
            confidence=0.92,
            entity_id="TRK-42",
            duration_seconds=95.0,
            action=None,
        )
        panel_mock.zone = "Cajas y Salida"
        situations = controller._extract_real_situations({"cam_09": panel_mock})
        self.assertEqual(len(situations), 1)
        self.assertEqual(situations[0]["type"], "PERMANENCIA_PROLONGADA")
        self.assertEqual(situations[0]["severity"], "HIGH")
        self.assertEqual(situations[0]["zone"], "Cajas y Salida")

    def test_zone_missing_yields_no_determinada(self):
        """Missing zone must yield 'No determinada', never 'Zona 01'."""
        controller = OperationalPanelsController()
        panel_mock = mock.MagicMock()
        panel_mock.situation = mock.MagicMock(
            situation_id="SIT-002",
            situation_type="ALERTA_ACCESO",
            severity="MEDIUM",
            confidence=0.85,
            entity_id=None,
            duration_seconds=10.0,
            action=None,
        )
        panel_mock.zone = None  # No zone configured
        situations = controller._extract_real_situations({"cam_02": panel_mock})
        self.assertEqual(len(situations), 1)
        self.assertEqual(situations[0]["zone"], "No determinada")

    def test_unspecified_agent_state_displays_no_disponible(self):
        """When agent controller is not attached, UI must display 'NO DISPONIBLE'."""
        controller = OperationalPanelsController()
        canvas = tk.Canvas(self.root, width=800, height=600)
        canvas.pack()
        self.root.update_idletasks()

        controller.render_view(
            OperationalCommandCenterModes.OVERVIEW,
            canvas,
            800,
            600,
            {"agent_state": None},  # No agent controller connected
            {},
        )
        all_text = [canvas.itemcget(item, "text") for item in canvas.find_all() if canvas.type(item) == "text"]
        self.assertTrue(any("NO DISPONIBLE" in t for t in all_text), "Must display 'NO DISPONIBLE' if agent state is missing")
        self.assertFalse(any("OBSERVANDO" in t for t in all_text), "Must NOT fabricate 'OBSERVANDO' without real agent state")

    def test_unspecified_autonomy_displays_no_certificada(self):
        """When autonomy policy is not configured, UI must display 'AUTONOMÍA: NO CERTIFICADA'."""
        controller = OperationalPanelsController()
        canvas = tk.Canvas(self.root, width=800, height=600)
        canvas.pack()
        self.root.update_idletasks()

        controller.render_view(
            OperationalCommandCenterModes.OVERVIEW,
            canvas,
            800,
            600,
            {"autonomy_level": None},
            {},
        )
        all_text = [canvas.itemcget(item, "text") for item in canvas.find_all() if canvas.type(item) == "text"]
        self.assertTrue(any("NO CERTIFICADA" in t for t in all_text), "Must display 'NO CERTIFICADA'")

    def test_side_panel_collapsed_by_default(self):
        """Technical side panel must be collapsed by default for video dominance."""
        ctrl_mock = mock.MagicMock()
        ctrl_mock.camera_ids = ["cam_01", "cam_02"]
        ctrl_mock.stores.return_value = ["Store A"]
        app = TkApp(self.root, ctrl_mock)
        self.assertFalse(app._side_panel_visible, "Side panel must be collapsed by default")


if __name__ == "__main__":
    unittest.main()
