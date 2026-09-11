"""Device settings backend tests (MACRO-OC-02, Bloques C/D/E).

Covers:
  - read_recorders exposes only NON-SENSITIVE fields
  - save_recorder regenerates physical cameras from host/port/profile
  - the password is never accepted or persisted (SECRET_LEAK=0)
  - credentials stay as a credential_ref (never plaintext)
  - the connection test is bounded and uses the certified opener (no custom
    Digest implementation)
  - structural validation via StoreCatalog after each save
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.deployment import device_config

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CONFIG = REPO_ROOT / "config" / "multistore.active.json"


class DeviceConfigBase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="tuke_cfg_"))
        self.config_path = self.tmp_dir / "multistore.active.json"
        shutil.copyfile(ACTIVE_CONFIG, self.config_path)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def load(self):
        with open(self.config_path, encoding="utf-8") as fh:
            return json.load(fh)


class TestReadRecorders(DeviceConfigBase):
    def test_physical_cameras_is_15_and_capacity_is_16(self):
        recorders = device_config.read_recorders(self.config_path)
        self.assertEqual(len(recorders), 1)
        rec = recorders[0]
        self.assertEqual(rec["physical_channels"], 15)
        self.assertEqual(rec["total_channels"], 16)

    def test_only_non_sensitive_fields_are_exposed(self):
        recorders = device_config.read_recorders(self.config_path)
        rec = recorders[0]
        self.assertNotIn("password", rec)
        self.assertNotIn("secret", rec)
        self.assertEqual(rec["host"], "186.103.177.83")
        self.assertEqual(rec["port"], 554)
        self.assertEqual(rec["credentials_ref"], "ENV_DVR_PRINCIPAL_CREDS")
        self.assertEqual(len(rec["camera_ids"]), 15)

    def test_camera_ids_are_cam_01_to_cam_15(self):
        rec = device_config.read_recorders(self.config_path)[0]
        self.assertEqual(rec["camera_ids"][0], "cam_01")
        self.assertEqual(rec["camera_ids"][-1], "cam_15")


class TestSaveRecorder(DeviceConfigBase):
    def test_save_regenerates_15_physical_cameras(self):
        device_config.save_recorder(
            self.config_path,
            "store_nicopoly_principal",
            {
                "recorder_id": "dvr_principal",
                "host": "186.103.177.83",
                "port": 554,
                "physical_channels": 15,
            },
        )
        rec = device_config.read_recorders(self.config_path)[0]
        self.assertEqual(rec["physical_channels"], 15)
        self.assertEqual(rec["total_channels"], 16)  # capacity preserved

    def test_save_updates_host_and_stream_profile(self):
        device_config.save_recorder(
            self.config_path,
            "store_nicopoly_principal",
            {
                "recorder_id": "dvr_principal",
                "host": "10.0.0.9",
                "port": 554,
                "physical_channels": 15,
                "stream_profile": "sub",
            },
        )
        rec = device_config.read_recorders(self.config_path)[0]
        self.assertEqual(rec["host"], "10.0.0.9")
        self.assertEqual(rec["stream_profile"], "sub")
        # sub profile -> primary subtype 1 (stream_main uses subtype=1)
        data = self.load()
        cam = data["multistore"]["stores"][0]["recorders"][0]["cameras"][0]
        self.assertIn("subtype=1", cam["stream_main"])
        self.assertIn("subtype=0", cam["stream_sub"])

    def test_password_is_never_persisted(self):
        device_config.save_recorder(
            self.config_path,
            "store_nicopoly_principal",
            {
                "recorder_id": "dvr_principal",
                "host": "186.103.177.83",
                "port": 554,
                "physical_channels": 15,
                "password": "SUPER-SECRETO-123",
                "credentials_ref": "ENV_DVR_PRINCIPAL_CREDS",
            },
        )
        blob = self.config_path.read_text(encoding="utf-8")
        self.assertNotIn("SUPER-SECRETO-123", blob)
        self.assertNotIn("password", blob)
        rec = device_config.read_recorders(self.config_path)[0]
        self.assertEqual(rec["credentials_ref"], "ENV_DVR_PRINCIPAL_CREDS")

    def test_save_creates_new_recorder(self):
        result = device_config.save_recorder(
            self.config_path,
            "store_nicopoly_principal",
            {
                "recorder_id": "dvr_norte",
                "recorder_name": "DVR Norte",
                "host": "192.168.1.20",
                "port": 554,
                "physical_channels": 4,
                "stream_profile": "main",
            },
        )
        self.assertTrue(result["is_new"])
        recs = device_config.read_recorders(self.config_path)
        self.assertEqual(len(recs), 2)
        nuevo = next(r for r in recs if r["recorder_id"] == "dvr_norte")
        self.assertEqual(nuevo["host"], "192.168.1.20")
        self.assertEqual(nuevo["physical_channels"], 4)
        self.assertEqual(nuevo["credentials_ref"], "ENV_DVR_PRINCIPAL_CREDS")

    def test_save_rejects_unknown_store(self):
        with self.assertRaises(ValueError):
            device_config.save_recorder(
                self.config_path, "store_inexistente",
                {"recorder_id": "dvr_x", "host": "1.2.3.4", "port": 554},
            )

    def test_save_rejects_zero_physical_channels(self):
        with self.assertRaises(ValueError):
            device_config.save_recorder(
                self.config_path,
                "store_nicopoly_principal",
                {"recorder_id": "dvr_principal", "host": "1.2.3.4",
                 "port": 554, "physical_channels": 0},
            )

    def test_save_validates_through_catalog(self):
        # A structurally broken save (no host) must not write anything.
        with self.assertRaises(ValueError):
            device_config.save_recorder(
                self.config_path,
                "store_nicopoly_principal",
                {"recorder_id": "dvr_principal", "host": "", "port": 554},
            )
        rec = device_config.read_recorders(self.config_path)[0]
        self.assertEqual(rec["host"], "186.103.177.83")  # unchanged


class TestConnectionProbe(DeviceConfigBase):
    def test_probe_uses_certified_opener_not_custom_digest(self):
        """The probe must go through CameraDescriptor.build_url -> RTSPSource."""
        captured = {}

        class FakeMeta:
            width = 640
            height = 480

        fake_source = mock.MagicMock()
        fake_source.open.return_value = FakeMeta()

        with mock.patch(
            "src.capture.source_manager.CameraDescriptor"
        ) as descriptor_cls, mock.patch(
            "src.capture.live_sources.RTSPSource", return_value=fake_source
        ) as source_cls:
            desc = descriptor_cls.return_value
            desc.build_url.return_value = "rtsp://u:p@h:554/cam/realmonitor?channel=1&subtype=0"
            result = device_config.probe_first_frame(
                host="186.103.177.83", port=554, channel=1, subtype=0,
                username="admin", password="pw",
            )
            descriptor_cls.assert_called_once()
            self.assertEqual(desc.build_url.call_count, 1)
            source_cls.assert_called_once()
            self.assertEqual(
                source_cls.call_args.kwargs["max_open_attempts"], 1,
                "probe must be bounded (single attempt)",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["resolution"], "640x480")
        self.assertEqual(result["error"], "")

    def test_probe_failure_returns_bounded_error(self):
        with mock.patch(
            "src.capture.live_sources.RTSPSource",
            side_effect=RuntimeError("boom"),
        ):
            result = device_config.probe_first_frame(
                host="x", port=554, username="", password=""
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "RuntimeError")

    def test_tcp_reachable_is_bounded(self):
        self.assertFalse(device_config.tcp_reachable("10.255.255.1", 554, timeout=0.1))


class TestProfileSubtype(unittest.TestCase):
    def test_primary_subtype_mapping(self):
        self.assertEqual(device_config.primary_subtype_for("main"), 0)
        self.assertEqual(device_config.primary_subtype_for("sub"), 1)
        self.assertEqual(device_config.primary_subtype_for("??"), 0)


class TestStoreAdmin(DeviceConfigBase):
    def test_read_stores(self):
        stores = device_config.read_stores(self.config_path)
        self.assertEqual(len(stores), 1)
        store = stores[0]
        self.assertEqual(store["store_id"], "store_nicopoly_principal")
        self.assertEqual(store["organization_name"], "Nicopoly Retail")
        self.assertTrue(store["enabled"])
        self.assertEqual(store["recorder_count"], 1)
        self.assertEqual(store["camera_count"], 15)

    def test_add_store(self):
        result = device_config.save_store(
            self.config_path,
            {
                "store_id": "store_nicopoly_sur",
                "store_name": "Nicopoly Sur",
                "organization_id": "org_nicopoly",
                "organization_name": "Nicopoly Retail",
                "timezone": "America/Santiago",
                "enabled": True,
            },
        )
        self.assertTrue(result["is_new"])
        stores = device_config.read_stores(self.config_path)
        self.assertEqual(len(stores), 2)
        nuevo = next(s for s in stores if s["store_id"] == "store_nicopoly_sur")
        self.assertEqual(nuevo["store_name"], "Nicopoly Sur")
        self.assertEqual(nuevo["recorder_count"], 0)

    def test_add_store_requires_name(self):
        with self.assertRaises(ValueError):
            device_config.save_store(self.config_path, {"store_id": "x", "store_name": ""})

    def test_edit_store(self):
        device_config.save_store(
            self.config_path,
            {
                "store_id": "store_nicopoly_principal",
                "store_name": "Nicopoly Centro Renombrada",
                "organization_id": "org_nicopoly",
                "organization_name": "Nicopoly Retail",
                "timezone": "America/Santiago",
                "enabled": True,
            },
        )
        stores = device_config.read_stores(self.config_path)
        self.assertEqual(stores[0]["store_name"], "Nicopoly Centro Renombrada")

    def test_disable_store_disables_its_cameras(self):
        device_config.set_store_enabled(
            self.config_path, "store_nicopoly_principal", False
        )
        stores = device_config.read_stores(self.config_path)
        self.assertFalse(stores[0]["enabled"])
        data = self.load()
        for cam in data["multistore"]["stores"][0]["recorders"][0]["cameras"]:
            self.assertFalse(cam["enabled"])

    def test_disable_last_store_is_valid_and_round_trips(self):
        # Structural validity must survive zero enabled cameras.
        device_config.set_store_enabled(
            self.config_path, "store_nicopoly_principal", False
        )
        data = self.load()
        self.assertFalse(data["multistore"]["stores"][0]["enabled"])


class TestRecorderAdmin(DeviceConfigBase):
    def test_disable_recorder_disables_its_cameras(self):
        device_config.set_recorder_enabled(
            self.config_path, "store_nicopoly_principal", "dvr_principal", False
        )
        data = self.load()
        rec = data["multistore"]["stores"][0]["recorders"][0]
        self.assertFalse(rec["enabled"])
        for cam in rec["cameras"]:
            self.assertFalse(cam["enabled"])

    def test_reenable_recorder_restores_cameras(self):
        device_config.set_recorder_enabled(
            self.config_path, "store_nicopoly_principal", "dvr_principal", True
        )
        data = self.load()
        rec = data["multistore"]["stores"][0]["recorders"][0]
        self.assertTrue(rec["enabled"])
        for cam in rec["cameras"]:
            self.assertTrue(cam["enabled"])


class TestCameraAdmin(DeviceConfigBase):
    def test_edit_camera_name_zone_enabled(self):
        device_config.save_camera(
            self.config_path,
            "store_nicopoly_principal",
            "dvr_principal",
            "cam_03",
            {"camera_name": "Caja 3", "zone": "Cajas", "enabled": False},
        )
        data = self.load()
        cam = data["multistore"]["stores"][0]["recorders"][0]["cameras"][2]
        self.assertEqual(cam["camera_name"], "Caja 3")
        self.assertEqual(cam["zone"], "Cajas")
        self.assertFalse(cam["enabled"])

    def test_edit_unknown_camera_rejected(self):
        with self.assertRaises(ValueError):
            device_config.save_camera(
                self.config_path,
                "store_nicopoly_principal",
                "dvr_principal",
                "cam_99",
                {"camera_name": "x"},
            )

    def test_save_recorder_preserves_camera_metadata(self):
        device_config.save_camera(
            self.config_path,
            "store_nicopoly_principal",
            "dvr_principal",
            "cam_05",
            {"camera_name": "Puerta Principal", "zone": "Acceso", "enabled": True},
        )
        device_config.save_recorder(
            self.config_path,
            "store_nicopoly_principal",
            {"recorder_id": "dvr_principal", "host": "10.0.0.9", "port": 554,
             "physical_channels": 15},
        )
        data = self.load()
        cam = data["multistore"]["stores"][0]["recorders"][0]["cameras"][4]
        self.assertEqual(cam["camera_name"], "Puerta Principal")
        self.assertEqual(cam["zone"], "Acceso")


if __name__ == "__main__":
    unittest.main()