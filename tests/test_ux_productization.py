"""Targeted Unit Tests for UX Productization, DesignTokens, and Localization (es-CL)."""

import unittest
from unittest import mock
import tkinter as tk

from src.localization.i18n import I18n, _, DEFAULT_LOCALE
from src.ui.design_tokens import DesignTokens
from src.ui.tk_operational_panels import (
    OperationalCommandCenterModes,
    OperationalPanelsController,
)
from src.ui.tk_view import TkApp


class TestUXProductization(unittest.TestCase):
    def setUp(self):
        I18n.set_locale("es-CL")

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
        root = tk.Tk()
        root.withdraw()
        try:
            controller = OperationalPanelsController()
            canvas = tk.Canvas(root, width=800, height=600)
            canvas.pack()
            root.update_idletasks()

            # Pass empty panels -> Must render nominal empty state with zero fake data
            controller.render_view(
                OperationalCommandCenterModes.OVERVIEW,
                canvas,
                800,
                600,
                {"status": "IDLE"},
                {},
            )
            # Canvas should have text containing SIN SITUACIONES ACTIVAS
            all_text = [canvas.itemcget(item, "text") for item in canvas.find_all() if canvas.type(item) == "text"]
            self.assertTrue(any("SIN SITUACIONES ACTIVAS" in t for t in all_text))
            self.assertTrue(any("COLA DE ATENCIÓN VACÍA" in t for t in all_text))
        finally:
            root.destroy()

    def test_focus_hd_hud_spanish_labels(self):
        root = tk.Tk()
        root.withdraw()
        try:
            canvas = tk.Canvas(root, width=640, height=480)
            canvas.pack()
            root.update_idletasks()

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
        finally:
            root.destroy()
