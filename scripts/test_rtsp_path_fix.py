#!/usr/bin/env python3
"""Tests de normalización de ruta RTSP (LOOP-0015-FIX).

FIX-01..FIX-12: completar /cam/realmonitor, no duplicar, preservar rutas
explícitas, conservar channel/subtype y seguridad de credenciales.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.capture.rtsp_url import build_rtsp_url
from src.observability.logging_setup import redact_rtsp_url

CANARY = "SECRET_CANARY_RTSP_TRACE_001"


def test_fix_01_host_sin_path_agrega_cam_realmonitor():
    """FIX-01: rtsp://host -> /cam/realmonitor"""
    url = build_rtsp_url("rtsp://host", "u", "p", channel=5, subtype=1)
    assert "rtsp://u:p@host/cam/realmonitor?channel=5&subtype=1" == url, url
    print("PASS: FIX-01 host sin path -> /cam/realmonitor")
    return True


def test_fix_02_host_con_puerto_agrega_cam_realmonitor():
    """FIX-02: rtsp://host:554 -> /cam/realmonitor"""
    url = build_rtsp_url("rtsp://host:554", "u", "p", channel=5, subtype=1)
    assert "rtsp://u:p@host:554/cam/realmonitor?channel=5&subtype=1" == url, url
    print("PASS: FIX-02 host:puerto -> /cam/realmonitor")
    return True


def test_fix_03_no_duplica_cam_realmonitor():
    """FIX-03: host con /cam/realmonitor -> no duplicar path"""
    url = build_rtsp_url("rtsp://host:554/cam/realmonitor", "u", "p", channel=5, subtype=1)
    assert url.count("/cam/realmonitor") == 1, url
    assert url.endswith("/cam/realmonitor?channel=5&subtype=1"), url
    print("PASS: FIX-03 no duplica /cam/realmonitor")
    return True


def test_fix_04_channel_1():
    """FIX-04: channel=1 correcto"""
    url = build_rtsp_url("rtsp://host:554", "u", "p", channel=1, subtype=1)
    assert "channel=1&subtype=1" in url, url
    print("PASS: FIX-04 channel=1")
    return True


def test_fix_05_channel_5():
    """FIX-05: channel=5 correcto"""
    url = build_rtsp_url("rtsp://host:554", "u", "p", channel=5, subtype=1)
    assert "channel=5&subtype=1" in url, url
    print("PASS: FIX-05 channel=5")
    return True


def test_fix_06_channel_7():
    """FIX-06: channel=7 correcto"""
    url = build_rtsp_url("rtsp://host:554", "u", "p", channel=7, subtype=1)
    assert "channel=7&subtype=1" in url, url
    print("PASS: FIX-06 channel=7")
    return True


def test_fix_07_subtype_preservado():
    """FIX-07: subtype=1 preservado (no cambia a 0)"""
    url = build_rtsp_url("rtsp://host:554", "u", "p", channel=5, subtype=1)
    assert "subtype=1" in url, url
    assert "subtype=0" not in url, url
    print("PASS: FIX-07 subtype=1 preservado")
    return True


def test_fix_08_password_caracteres_especiales():
    """FIX-08: password con caracteres especiales preservado/codificado"""
    password = "P@ss:w%rd#1?&"
    url = build_rtsp_url("rtsp://host:554", "test_user", password, channel=5, subtype=1)
    # El password debe estar percent-codificado y presente en la URL en memoria
    assert "test_user" in url, url
    assert "%" in url, url
    # La forma redactada nunca contiene el secreto
    redacted = redact_rtsp_url(url)
    assert password not in redacted, redacted
    assert "test_user" not in redacted, redacted
    assert "REDACTED:REDACTED" in redacted, redacted
    print("PASS: FIX-08 password especial codificado y redactado")
    return True


def test_fix_09_url_redactada_sin_secretos():
    """FIX-09: URL redactada sin secretos"""
    url = build_rtsp_url("rtsp://host:554", "admin", CANARY, channel=5, subtype=1)
    redacted = redact_rtsp_url(url)
    assert CANARY not in redacted, redacted
    assert "admin" not in redacted, redacted
    assert "REDACTED:REDACTED" in redacted, redacted
    assert "/cam/realmonitor?channel=5&subtype=1" in redacted, redacted
    print("PASS: FIX-09 URL redactada sin secretos")
    return True


def test_fix_10_ruta_explicita_preservada():
    """FIX-10: ruta explícita diferente no se sobrescribe"""
    url = build_rtsp_url("rtsp://host:554/custom/path", "u", "p", channel=3, subtype=1)
    assert "/custom/path?channel=3&subtype=1" in url, url
    assert "/cam/realmonitor" not in url, url
    print("PASS: FIX-10 ruta explícita preservada")
    return True


def test_fix_11_selector_existente_sin_regresion():
    """FIX-11: selector existente sin regresión (suite LOOP-0014)"""
    from scripts.test_channel_selector import run_all_tests

    assert run_all_tests(), "Suite de selector (LOOP-0014) falló"
    print("PASS: FIX-11 selector existente sin regresión")
    return True


def test_fix_12_file_webcam_sin_cambios():
    """FIX-12: FILE/WEBCAM sin cambios (suite de seguridad existente)"""
    from scripts.test_secret_leak import run_all_tests

    assert run_all_tests(), "Suite de seguridad (AC-SEC) falló"
    print("PASS: FIX-12 FILE/WEBCAM sin cambios")
    return True


def run_all_tests():
    tests = [
        test_fix_01_host_sin_path_agrega_cam_realmonitor,
        test_fix_02_host_con_puerto_agrega_cam_realmonitor,
        test_fix_03_no_duplica_cam_realmonitor,
        test_fix_04_channel_1,
        test_fix_05_channel_5,
        test_fix_06_channel_7,
        test_fix_07_subtype_preservado,
        test_fix_08_password_caracteres_especiales,
        test_fix_09_url_redactada_sin_secretos,
        test_fix_10_ruta_explicita_preservada,
        test_fix_11_selector_existente_sin_regresion,
        test_fix_12_file_webcam_sin_cambios,
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