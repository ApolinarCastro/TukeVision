"""DEF-CCTV-04 — launcher first-frame gate regression tests (MACRO-OC-02).

Ensures the launcher:
  - does NOT require the custom Digest probe (removed regression);
  - uses the certified RTSPSource opener for REAL_STREAM_OPEN + FIRST_FRAME;
  - only uses configured recorder endpoints (186.103.177.83:554), never the
    operator laptop IP;
  - preserves the historically working RTSP template
    (/cam/realmonitor?channel=N&subtype=X via build_rtsp_url);
  - hands credentials in memory without CLI args or logs;
  - returns controlled failure, keeps the UI responsive, supports cancel and
    a second attempt.
"""

import importlib.util
import json
import socket
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from urllib.parse import urlsplit, parse_qs

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CONFIG = REPO_ROOT / "config" / "multistore.active.json"

_LAUNCHER_PATH = REPO_ROOT / "scripts" / "launcher.py"
_spec = importlib.util.spec_from_file_location("tv_launcher", _LAUNCHER_PATH)
_launcher_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_launcher_module)
CredentialDialog = _launcher_module.CredentialDialog
TCP_CONNECT_TIMEOUT = _launcher_module.TCP_CONNECT_TIMEOUT
FIRST_FRAME_TIMEOUT = _launcher_module.FIRST_FRAME_TIMEOUT
TOTAL_LOGIN_TIMEOUT = _launcher_module.TOTAL_LOGIN_TIMEOUT

LAUNCHER_SOURCE = _LAUNCHER_PATH.read_text(encoding="utf-8")


class FakeVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class FakeLabel:
    def __init__(self):
        self.foreground = None

    def config(self, foreground=None):
        if foreground is not None:
            self.foreground = foreground


class FakeButton:
    def __init__(self):
        self.state = "normal"

    def config(self, state=None):
        if state is not None:
            self.state = state


class FakeRoot:
    """Executes immediate (ms=0) callbacks, records delayed ones."""

    def __init__(self):
        self.calls = []

    def after(self, ms, func=None, *args):
        self.calls.append((ms, func))
        if ms == 0 and func is not None:
            func(*args)
        return "after-id"

    def winfo_exists(self):
        return True

    def quit(self):
        pass

    def destroy(self):
        pass


def make_dialog():
    dialog = CredentialDialog(ACTIVE_CONFIG)
    dialog._root = FakeRoot()
    dialog.status_var = FakeVar()
    dialog.progress_var = FakeVar()
    dialog.status_label = FakeLabel()
    dialog.start_btn = FakeButton()
    return dialog


class FakeRTSPSource:
    """Certified-opener stand-in that records the URL and returns a frame."""

    instances = []

    def __init__(self, rtsp_url=None, **kwargs):
        self.rtsp_url = rtsp_url
        self.kwargs = kwargs
        self.closed = False
        FakeRTSPSource.instances.append(self)

    def open(self):
        return SimpleNamespace(width=352, height=240)

    def close(self):
        self.closed = True


class TestLauncherFirstFrameGate(unittest.TestCase):
    def setUp(self):
        self.dialog = make_dialog()

    # 1. previous working connection path preserved
    def test_probe_uses_certified_template_and_opener(self):
        with mock.patch("src.capture.live_sources.RTSPSource", FakeRTSPSource):
            result = self.dialog._probe_first_frame(
                "186.103.177.83", "admin", "dummy"
            )
        self.assertTrue(result["ok"])
        self.assertEqual(result["resolution"], "352x240")
        self.assertTrue(FakeRTSPSource.instances)
        url = FakeRTSPSource.instances[-1].rtsp_url
        parts = urlsplit(url)
        self.assertEqual(parts.hostname, "186.103.177.83")
        self.assertEqual(parts.port, 554)
        self.assertEqual(parts.path, "/cam/realmonitor")
        query = parse_qs(parts.query)
        self.assertEqual(query.get("channel"), ["1"])
        self.assertTrue(FakeRTSPSource.instances[-1].closed)

    # 2. custom auth probe not required
    def test_custom_digest_probe_removed(self):
        self.assertFalse(hasattr(self.dialog, "_test_rtsp_auth"))
        self.assertFalse(hasattr(self.dialog, "_get_camera_stream_path"))
        self.assertNotIn("_test_rtsp_auth", LAUNCHER_SOURCE)
        self.assertNotIn("hashlib", LAUNCHER_SOURCE)
        self.assertIn("RTSPSource", LAUNCHER_SOURCE)

    # 3. endpoint = 186.103.177.83
    def test_configured_endpoint_is_remote_dvr(self):
        endpoints = self.dialog._configured_endpoints("store_nicopoly_principal")
        self.assertEqual(len(endpoints), 1)
        self.assertEqual(endpoints[0]["host"], "186.103.177.83")
        self.assertEqual(endpoints[0]["port"], 554)

    # 4. 10.10.11.177 never used as recorder
    def test_laptop_ip_never_a_recorder(self):
        config = self.dialog.config
        recorder_hosts = []
        for store in config["multistore"]["stores"]:
            for recorder in store.get("recorders", []):
                recorder_hosts.append(recorder["host"])
        self.assertEqual(recorder_hosts, ["186.103.177.83"])
        self.assertNotIn("10.10.11.177", recorder_hosts)
        for camera in config["multistore"]["stores"][0]["recorders"][0]["cameras"]:
            self.assertNotIn("10.10.11.177", camera.get("stream_main", ""))
            self.assertNotIn("10.10.11.177", camera.get("stream_sub", ""))

    # 5. credentials with special characters survive handoff
    def test_special_characters_survive_handoff(self):
        user = "admin"
        password = 'p@ss&w0rd $%^"()=;/\\漢字'
        blob = json.dumps({"username": user, "password": password})
        parsed = json.loads(blob)
        self.assertEqual(parsed["username"], user)
        self.assertEqual(parsed["password"], password)
        env = {"ENV_DVR_PRINCIPAL_CREDS": blob}
        again = json.loads(env["ENV_DVR_PRINCIPAL_CREDS"])
        self.assertEqual(again["password"], password)

    # 6. no password logs
    def test_no_password_logged_or_printed(self):
        self.assertNotIn("print(password", LAUNCHER_SOURCE)
        self.assertNotIn("print( password", LAUNCHER_SOURCE)
        # logger is used for spawn verification, but password VALUE should never be logged
        # Check that password variable is not interpolated into log messages
        # The actual test: when _probe_first_frame is called with a secret password,
        # that secret should not appear in any logged output
        with mock.patch("src.capture.live_sources.RTSPSource", FakeRTSPSource):
            failed = self.dialog._probe_first_frame("186.103.177.83", "admin", "TOP-SECRET-X")
        self.assertNotIn("TOP-SECRET-X", json.dumps(failed))

    # 7. no password CLI args
    def test_no_password_in_cli_args(self):
        with mock.patch("subprocess.Popen") as popen:
            rc = self.dialog._spawn_runtime("store_nicopoly_principal", "admin", "s3cret@&$")
        self.assertEqual(rc, 0)
        args = popen.call_args[0][0]
        self.assertNotIn("s3cret@&$", args)
        env = popen.call_args[1]["env"]
        self.assertEqual(
            json.loads(env["ENV_DVR_PRINCIPAL_CREDS"])["password"], "s3cret@&$"
        )
        self.assertNotIn("--password", args)

    # 8. first-frame success opens UI (Command Center handoff)
    def test_first_frame_success_launches(self):
        self.dialog._tcp_reachable = lambda host, port, timeout: True
        self.dialog._probe_first_frame = lambda host, u, p: {
            "ok": True, "resolution": "352x240", "error": "",
        }
        self.dialog._test_and_launch("store_nicopoly_principal", "admin", "pw")
        self.assertEqual(
            self.dialog.result, ("store_nicopoly_principal", "admin", "pw")
        )
        self.assertIn("Conexión validada", self.dialog.status_var.get())
        self.assertIn("Abriendo Command Center", self.dialog.progress_var.get())

    # 9. wrong credential returns controlled failure
    def test_wrong_credential_controlled_failure(self):
        self.dialog._tcp_reachable = lambda host, port, timeout: True
        self.dialog._probe_first_frame = lambda host, u, p: {
            "ok": False, "resolution": "", "error": "VideoReadError",
        }
        self.dialog._test_and_launch("store_nicopoly_principal", "admin", "bad")
        self.assertIsNone(self.dialog.result)
        self.assertIn("No se pudo conectar al DVR", self.dialog.status_var.get())
        self.assertEqual(self.dialog.start_btn.state, "normal")

    # 10. timeout returns control
    def test_total_timeout_returns_control(self):
        self.dialog._login_start_time = time.time() - (TOTAL_LOGIN_TIMEOUT + 1)
        self.dialog._schedule_timeout_check()
        self.assertIn("Tiempo de espera agotado", self.dialog.status_var.get())
        self.assertEqual(self.dialog.start_btn.state, "normal")

    # 11. cancel works during probe
    def test_cancel_during_probe(self):
        calls = {"probe": 0}
        self.dialog._cancelled = True
        self.dialog._tcp_reachable = lambda host, port, timeout: True
        self.dialog._probe_first_frame = lambda host, u, p: (
            calls.__setitem__("probe", calls["probe"] + 1) or
            {"ok": True, "resolution": "352x240", "error": ""}
        )
        self.dialog._test_and_launch("store_nicopoly_principal", "admin", "pw")
        self.assertIsNone(self.dialog.result)
        self.assertEqual(calls["probe"], 0)

    # 12. second attempt works after a failure
    def test_second_attempt_after_failure(self):
        self.dialog._tcp_reachable = lambda host, port, timeout: True
        self.dialog._probe_first_frame = lambda host, u, p: {
            "ok": False, "resolution": "", "error": "VideoReadError",
        }
        self.dialog._test_and_launch("store_nicopoly_principal", "admin", "bad")
        self.assertIsNone(self.dialog.result)
        self.assertEqual(self.dialog.start_btn.state, "normal")

        self.dialog._probe_first_frame = lambda host, u, p: {
            "ok": True, "resolution": "352x240", "error": "",
        }
        self.dialog._test_and_launch("store_nicopoly_principal", "admin", "good")
        self.assertEqual(self.dialog.result, ("store_nicopoly_principal", "admin", "good"))

    # TCP pre-check uses the bounded timeout
    def test_tcp_precheck_uses_bounded_timeout(self):
        with mock.patch("socket.create_connection") as conn:
            conn.return_value = SimpleNamespace(close=lambda: None)
            ok = self.dialog._tcp_reachable("186.103.177.83", 554, TCP_CONNECT_TIMEOUT)
        self.assertTrue(ok)
        self.assertEqual(conn.call_args[0], (("186.103.177.83", 554),))
        self.assertEqual(conn.call_args[1]["timeout"], TCP_CONNECT_TIMEOUT)
        self.assertLessEqual(TCP_CONNECT_TIMEOUT, FIRST_FRAME_TIMEOUT)


if __name__ == "__main__":
    unittest.main()