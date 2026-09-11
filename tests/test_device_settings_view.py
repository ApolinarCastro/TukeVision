"""Device settings view tests (MACRO-OC-02, Bloques B/C/D).

The CONFIGURACIÓN -> DISPOSITIVOS admin window must:
  - open from the app (entry point exists)
  - mask the password field (show="*")
  - never persist the password on GUARDAR
  - expose GUARDAR and PROBAR CONEXIÓN actions
"""

import json
import shutil
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

from tests.conftest import shared_root
from src.ui.device_settings_view import (
    DeviceSettingsWindow,
    NEW_RECORDER,
    StoreEditorWindow,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CONFIG = REPO_ROOT / "config" / "multistore.active.json"


class DeviceSettingsViewBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # One Tk root per process avoids flaky ttk theme reloads on Windows.
        cls.root = shared_root()

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="tuke_view_"))
        self.config_path = self.tmp_dir / "multistore.active.json"
        shutil.copyfile(ACTIVE_CONFIG, self.config_path)
        self.window = DeviceSettingsWindow(self.root, self.config_path)

    def tearDown(self):
        try:
            self.window.destroy()
        except tk.TclError:
            pass
        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except tk.TclError:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


class TestDeviceSettingsWindow(DeviceSettingsViewBase):
    def test_window_opens_with_title(self):
        self.assertEqual(self.window.title(), "Configuración · Dispositivos")

    def test_password_field_is_masked(self):
        password_widget = self.window._entries["password"][1]
        self.assertEqual(password_widget.cget("show"), "*")

    def test_form_has_required_fields(self):
        for key in (
            "recorder_name", "recorder_type", "vendor", "host", "port",
            "device_port", "username_default", "password", "physical_channels",
            "stream_profile",
        ):
            self.assertIn(key, self.window._entries, f"missing field {key}")

    def test_has_save_and_test_buttons(self):
        self.assertEqual(self.window._save_btn.cget("text"), "GUARDAR")
        self.assertEqual(self.window._test_btn.cget("text"), "PROBAR CONEXIÓN")

    def test_editing_existing_recorder_populates_non_sensitive_fields(self):
        self.window._recorder_var.set("dvr_principal")
        self.window._on_recorder_change()
        self.assertEqual(self.window._field("host"), "186.103.177.83")
        self.assertEqual(self.window._field("port"), "554")
        self.assertEqual(self.window._field("username_default"), "admin")
        self.assertEqual(self.window._field("physical_channels"), "15")
        # password is never shown after load
        self.assertEqual(self.window._entries["password"][0].get(), "")

    def test_save_does_not_persist_password(self):
        self.window._recorder_var.set("dvr_principal")
        self.window._on_recorder_change()
        self.window._entries["password"][0].set("MI-CLAVE-SECRETA")
        with mock.patch(
            "src.ui.device_settings_view.messagebox.showerror"
        ) as mock_error:
            self.window._on_save()
            mock_error.assert_not_called()
        blob = self.config_path.read_text(encoding="utf-8")
        self.assertNotIn("MI-CLAVE-SECRETA", blob)
        self.assertNotIn("password", blob)
        # widget is cleared after save
        self.assertEqual(self.window._entries["password"][0].get(), "")

    def test_save_persists_non_sensitive_changes(self):
        self.window._recorder_var.set("dvr_principal")
        self.window._on_recorder_change()
        self.window._entries["host"][0].set("10.0.0.50")
        self.window._entries["physical_channels"][0].set("8")
        with mock.patch(
            "src.ui.device_settings_view.messagebox.showerror"
        ) as mock_error:
            self.window._on_save()
            mock_error.assert_not_called()
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        recorder = data["multistore"]["stores"][0]["recorders"][0]
        self.assertEqual(recorder["host"], "10.0.0.50")
        self.assertEqual(len(recorder["cameras"]), 8)
        self.assertEqual(recorder["credentials_ref"], "ENV_DVR_PRINCIPAL_CREDS")

    def test_connection_test_is_bounded_and_uses_certified_opener(self):
        self.window._recorder_var.set("dvr_principal")
        self.window._on_recorder_change()
        self.window._entries["password"][0].set("pw")

        class FakeThread:
            def __init__(self, target=None, daemon=None):
                self.target = target

            def start(self):
                self.target()

        with mock.patch(
            "src.ui.device_settings_view.tcp_reachable", return_value=True
        ) as mock_tcp, mock.patch(
            "src.ui.device_settings_view.probe_first_frame"
        ) as mock_probe, mock.patch(
            "src.ui.device_settings_view.threading.Thread", FakeThread
        ):
            self.window._on_test()
            mock_tcp.assert_called_once()
            mock_probe.assert_called_once_with(
                host="186.103.177.83", port=554, channel=1, subtype=0,
                username="admin", password="pw", timeout_s=6.0,
            )
            self.assertTrue(self.window._busy)


def _button_texts(widget):
    texts = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Button):
            texts.append(child.cget("text"))
        texts.extend(_button_texts(child))
    return texts


class TestAdminGates(DeviceSettingsViewBase):
    """BLOCK O: operator-visible gates for store / recorder / camera admin."""

    def test_operator_sees_plus_nueva_tienda(self):
        self.assertIn("+ NUEVA TIENDA", _button_texts(self.window))

    def test_operator_sees_plus_nuevo_dispositivo(self):
        self.assertIn("+ NUEVO DISPOSITIVO", _button_texts(self.window))

    def test_operator_sees_disable_actions(self):
        texts = _button_texts(self.window)
        self.assertEqual(texts.count("DESHABILITAR"), 2, "store + recorder disable")

    def test_camera_table_lists_15_cameras(self):
        self.window._recorder_var.set("dvr_principal")
        self.window._on_recorder_change()
        rows = self.window._cam_tree.get_children()
        self.assertEqual(len(rows), 15)
        values = self.window._cam_tree.item(rows[0], "values")
        self.assertEqual(values[1], "cam_01")
        self.assertEqual(values[3], "General")
        self.assertEqual(values[4], "SÍ")

    def test_selecting_camera_populates_edit_fields(self):
        self.window._recorder_var.set("dvr_principal")
        self.window._on_recorder_change()
        self.window._cam_tree.selection_set("cam_03")
        self.window._on_camera_select()
        self.assertEqual(self.window._cam_name_var.get(), "Cámara 03")
        self.assertEqual(self.window._cam_zone_var.get(), "General")
        self.assertTrue(self.window._cam_enabled_var.get())

    def test_camera_edit_persists_name_zone(self):
        self.window._recorder_var.set("dvr_principal")
        self.window._on_recorder_change()
        self.window._cam_tree.selection_set("cam_05")
        self.window._on_camera_select()
        self.window._cam_name_var.set("Puerta Trasera")
        self.window._cam_zone_var.set("Salida")
        self.window._on_save_camera()
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        cam = data["multistore"]["stores"][0]["recorders"][0]["cameras"][4]
        self.assertEqual(cam["camera_name"], "Puerta Trasera")
        self.assertEqual(cam["zone"], "Salida")

    def test_store_editor_saves_new_store(self):
        dialog = StoreEditorWindow(self.root, self.config_path)
        dialog._store_id.set("store_nicopoly_sur")
        dialog._store_name.set("Nicopoly Sur")
        dialog._org_id.set("org_nicopoly")
        dialog._org_name.set("Nicopoly Retail")
        dialog._timezone.set("America/Santiago")
        dialog._on_save()
        dialog.destroy()
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        stores = data["multistore"]["stores"]
        self.assertEqual(len(stores), 2)
        self.assertEqual(stores[1]["store_id"], "store_nicopoly_sur")
        self.assertTrue(stores[1]["enabled"])

    def test_store_editor_edit_persists_enabled_flag(self):
        dialog = StoreEditorWindow(
            self.root, self.config_path,
            {"store_id": "store_nicopoly_principal", "store_name": "Centro",
             "organization_id": "org_nicopoly", "organization_name": "Retail",
             "timezone": "America/Santiago", "enabled": False},
        )
        dialog._enabled.set(False)
        dialog._on_save()
        dialog.destroy()
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertFalse(data["multistore"]["stores"][0]["enabled"])


class TestTkAppDeviceSettingsEntry(unittest.TestCase):
    def test_tk_view_has_configuration_button(self):
        from src.ui.tk_view import TkApp

        self.assertTrue(hasattr(TkApp, "_open_device_settings"))


if __name__ == "__main__":
    unittest.main()