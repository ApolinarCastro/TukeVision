#!/usr/bin/env python3
"""Tests de trazabilidad RTSP UI -> controller -> RTSPSource (LOOP-0015-TRACE).

Cubre TRACE-01 a TRACE-08 del alcance del loop. Modo EXPERIMENTAL_TRACE_ONLY:
solo observabilidad, sin modificar lógica del producto.

Se ejecuta sobre los módulos reales instrumentados:
  - src/ui/tk_view.py          (RTSP_SELECTED_CHANNEL, RTSP_FINAL_URL_REDACTED)
  - src/ui/controller.py       (SOURCE_TYPE, RTSP_CONTROLLER_VALUE_REDACTED)
  - src/capture/live_sources.py(RTSP_SOURCE_URL_REDACTED)

No abre conexiones de red: el controlador usa un pipeline/source dummy y el
RTSPSource se instancia sin llamar a open().
"""

import io
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CANARY = "SECRET_CANARY_RTSP_TRACE_001"
HOST = "rtsp://186.103.177.83:554/cam/realmonitor"
USERNAME = "admin"
CHANNEL = 5


class FakeController:
    """Controlador ficticio que solo registra lo que recibe de la vista."""

    def __init__(self) -> None:
        self.calls = []

    def start(self, kind: str, value: str) -> None:
        self.calls.append((kind, value))

    def stop(self) -> None:
        pass

    def close(self) -> None:
        pass


class DummySource:
    source_type = "RTSP"


class DummyPipeline:
    def process_source(self, source, on_frame=None):
        class _Summary:
            final_status = "OK"
            video_path = "dummy"

        return _Summary()


class LogCapture:
    """Captura los registros de los loggers TukeVision en un buffer."""

    def __init__(self, names=("tukevision.ui", "tukevision.capture")) -> None:
        from src.observability.logging_setup import RedactingFormatter

        self.buffer = io.StringIO()
        self.handler = logging.StreamHandler(self.buffer)
        self.handler.setFormatter(RedactingFormatter("%(message)s"))
        self.handler.setLevel(logging.INFO)
        self._loggers = [logging.getLogger(n) for n in names]
        self._old_levels = []
        for logger in self._loggers:
            self._old_levels.append(logger.level)
            logger.setLevel(logging.INFO)
            logger.addHandler(self.handler)
            logger.propagate = False

    def lines(self) -> list:
        return self.buffer.getvalue().splitlines()

    def text(self) -> str:
        return self.buffer.getvalue()

    def close(self) -> None:
        for logger, level in zip(self._loggers, self._old_levels):
            logger.removeHandler(self.handler)
            logger.setLevel(level)
            logger.propagate = True


def _build_url() -> str:
    from src.capture.rtsp_url import build_rtsp_url

    return build_rtsp_url(HOST, USERNAME, CANARY, channel=CHANNEL, subtype=1)


def _make_tkapp(controller):
    import tkinter as tk

    from src.ui.tk_view import TkApp

    root = tk.Tk()
    root.withdraw()
    app = TkApp(root, controller)
    return root, app


def test_trace_01_view_logs_selected_channel():
    """TRACE-01: selector=5 -> log contiene RTSP_SELECTED_CHANNEL=5."""
    cap = LogCapture()
    try:
        root, app = _make_tkapp(FakeController())
        try:
            app._source_var.set("RTSP")
            app._rtsp_host_var.set(HOST)
            app._rtsp_user_var.set(USERNAME)
            app._rtsp_pass_var.set(CANARY)
            app._rtsp_channel_var.set(str(CHANNEL))
            app._on_start()
        finally:
            root.destroy()
        text = cap.text()
        assert "RTSP_SELECTED_CHANNEL=5" in text, text
        print("PASS: TRACE-01 selector=5 -> RTSP_SELECTED_CHANNEL=5")
        return True
    finally:
        cap.close()


def test_trace_02_logged_url_contains_channel_subtype():
    """TRACE-02: URL final logueada contiene channel=5&subtype=1."""
    cap = LogCapture()
    try:
        root, app = _make_tkapp(FakeController())
        try:
            app._source_var.set("RTSP")
            app._rtsp_host_var.set(HOST)
            app._rtsp_user_var.set(USERNAME)
            app._rtsp_pass_var.set(CANARY)
            app._rtsp_channel_var.set(str(CHANNEL))
            app._on_start()
        finally:
            root.destroy()
        text = cap.text()
        assert "channel=5&subtype=1" in text, text
        print("PASS: TRACE-02 URL final con channel=5&subtype=1")
        return True
    finally:
        cap.close()


def test_trace_03_logged_url_is_redacted():
    """TRACE-03: URL logueada está redactada (sin credenciales)."""
    cap = LogCapture()
    try:
        root, app = _make_tkapp(FakeController())
        try:
            app._source_var.set("RTSP")
            app._rtsp_host_var.set(HOST)
            app._rtsp_user_var.set(USERNAME)
            app._rtsp_pass_var.set(CANARY)
            app._rtsp_channel_var.set(str(CHANNEL))
            app._on_start()
        finally:
            root.destroy()
        text = cap.text()
        assert "REDACTED:REDACTED" in text, text
        assert CANARY not in text, "canary (password) visible en logs"
        assert USERNAME not in text, "usuario visible en logs"
        print("PASS: TRACE-03 URL logueada redactada")
        return True
    finally:
        cap.close()


def test_trace_04_controller_receives_same_redacted_url():
    """TRACE-04: el controller recibe la misma URL redactada conceptualmente."""
    from src.observability.logging_setup import redact_rtsp_url
    from src.ui.controller import UiController

    url = _build_url()
    expected = redact_rtsp_url(url)

    cap = LogCapture()
    try:
        controller = UiController(
            config={},
            source_builder=lambda kind, inp, cfg: DummySource(),
            pipeline_factory=lambda: DummyPipeline(),
        )
        controller.start("RTSP", url)
        controller.join(timeout=5.0)
        controller.close()

        text = cap.text()
        assert "SOURCE_TYPE=RTSP" in text, text
        assert f"RTSP_CONTROLLER_VALUE_REDACTED={expected}" in text, text
        assert CANARY not in text, "canary visible en logs del controller"
        print("PASS: TRACE-04 controller recibe misma URL redactada")
        return True
    finally:
        cap.close()


def test_trace_05_rtspsource_receives_same_url():
    """TRACE-05: RTSPSource recibe la misma URL (redactada conceptualmente)."""
    from src.capture.live_sources import RTSPSource
    from src.observability.logging_setup import redact_rtsp_url

    url = _build_url()
    expected = redact_rtsp_url(url)

    cap = LogCapture()
    try:
        source = RTSPSource(rtsp_url=url)
        assert source is not None
        text = cap.text()
        assert f"RTSP_SOURCE_URL_REDACTED={expected}" in text, text
        assert CANARY not in text, "canary visible en logs de RTSPSource"
        print("PASS: TRACE-05 RTSPSource recibe misma URL")
        return True
    finally:
        cap.close()


def test_trace_06_canary_not_in_logs():
    """TRACE-06: el canary no aparece en stdout/stderr/logs."""
    import contextlib

    from src.observability.logging_setup import redact_rtsp_url

    url = _build_url()
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    cap = LogCapture()

    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            print(f"RTSP_FINAL_URL_REDACTED={redact_rtsp_url(url)}")
            print(f"RTSP_CONTROLLER_VALUE_REDACTED={redact_rtsp_url(url)}")
            print(f"RTSP_SOURCE_URL_REDACTED={redact_rtsp_url(url)}")

        combined = (
            cap.text() + "\n" + stdout_buf.getvalue() + "\n" + stderr_buf.getvalue()
        )
        assert CANARY not in combined, "canary visible en alguna salida"
        assert "PASSWORD_VISIBLE" not in combined
        print("PASS: TRACE-06 canary no aparece en salidas")
        return True
    finally:
        cap.close()


def test_trace_07_file_source_unaffected():
    """TRACE-07: FILE source no produce trazas RTSP."""
    cap = LogCapture()
    try:
        root, app = _make_tkapp(FakeController())
        try:
            app._source_var.set("FILE")
            app._input_var.set("dummy.mp4")
            app._on_start()
        finally:
            root.destroy()
        text = cap.text()
        assert "RTSP_" not in text, text
        assert "SOURCE_TYPE=" not in text, text
        print("PASS: TRACE-07 FILE source sin trazas RTSP")
        return True
    finally:
        cap.close()


def test_trace_08_webcam_source_unaffected():
    """TRACE-08: WEBCAM source no produce trazas RTSP."""
    cap = LogCapture()
    try:
        root, app = _make_tkapp(FakeController())
        try:
            app._source_var.set("WEBCAM")
            app._input_var.set("0")
            app._on_start()
        finally:
            root.destroy()
        text = cap.text()
        assert "RTSP_" not in text, text
        assert "SOURCE_TYPE=" not in text, text
        print("PASS: TRACE-08 WEBCAM source sin trazas RTSP")
        return True
    finally:
        cap.close()


def run_all_tests():
    tests = [
        test_trace_01_view_logs_selected_channel,
        test_trace_02_logged_url_contains_channel_subtype,
        test_trace_03_logged_url_is_redacted,
        test_trace_04_controller_receives_same_redacted_url,
        test_trace_05_rtspsource_receives_same_url,
        test_trace_06_canary_not_in_logs,
        test_trace_07_file_source_unaffected,
        test_trace_08_webcam_source_unaffected,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
    print(f"\nResultado: {passed} PASS, {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if run_all_tests() else 1)