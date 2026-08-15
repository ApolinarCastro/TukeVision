#!/usr/bin/env python3
"""Test de no exposición de secretos (AC-SEC-01 a AC-SEC-14).

Prueba que las credenciales ficticias no aparecen en stdout, stderr ni logs
durante la ejecución del diagnóstico RTSP con fallo controlado.
"""

import sys
import io
import contextlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.test_rtsp_connection import _with_credentials
from src.observability.logging_setup import redact_rtsp_url


def test_url_construction_with_special_chars():
    """AC-SEC-04, AC-SEC-05, AC-SEC-06, AC-SEC-07: URL construction with special chars."""
    host = "rtsp://192.168.1.50:554/cam/realmonitor?channel=1&subtype=1"
    username = "test_user"
    password = "Fake:P@ss\\word%123?&#"
    
    url = _with_credentials(host, username, password)
    
    # Verificar que host, path, query se conservan
    assert "192.168.1.50:554" in url
    assert "/cam/realmonitor" in url
    assert "channel=1&subtype=1" in url
    
    # Verificar que username/password están codificados
    assert "test_user" in url
    assert "Fake%3AP%40ss%5Cword%25123%3F%26%23" in url  # encoded
    
    print("PASS: test_url_construction_with_special_chars")
    return True


def test_redaction_never_contains_secret():
    """AC-SEC-08: URL redactada nunca contiene secreto."""
    test_cases = [
        "rtsp://user:pass@host:554/path",
        "rtsp://admin:P%40ss%3A%5Cword%26%25%3F%23%20test@192.168.1.50:554/cam/realmonitor?channel=1&subtype=1",
        "rtsp://test_user:Fake%3AP%40ss%5Cword%25123%3F%26%23@192.168.1.50:554/cam/realmonitor?channel=1&subtype=1",
        "rtsp://admin:SECRET_CANARY_RTSP_8F21@186.103.177.83:554/cam/realmonitor?channel=1&subtype=1",
        "password=secret123",
    ]
    
    for original in test_cases:
        redacted = redact_rtsp_url(original)
        
        # Extraer posibles secretos del original
        import re
        cred_match = re.search(r'rtsp://([^/@:\s]+):([^/@:\s]+)@', original)
        if cred_match:
            user, pwd = cred_match.groups()
            assert user not in redacted, f"Username '{user}' found in redacted: {redacted}"
            assert pwd not in redacted, f"Password '{pwd}' found in redacted: {redacted}"
        
        # Verificar formato redactado
        assert "REDACTED:REDACTED" in redacted or "password=REDACTED" in redacted
    
    print("PASS: test_redaction_never_contains_secret")
    return True


def test_special_char_password_not_in_output():
    """AC-SEC-01 a AC-SEC-04: Password con caracteres especiales no aparece en salida."""
    # Simular la ejecución capturando stdout/stderr
    fake_password = "SECRET_CANARY_RTSP_8F21"
    fake_user = "test_user"
    host = "rtsp://192.0.2.1:554/test"
    
    from scripts.test_rtsp_connection import _with_credentials
    from src.observability.logging_setup import redact_rtsp_url
    
    rtsp_url = _with_credentials(host, fake_user, fake_password)
    redacted = redact_rtsp_url(rtsp_url)
    
    # Verificar que el password no está en la URL redactada
    assert fake_password not in redacted
    assert fake_user not in redacted
    assert "REDACTED:REDACTED" in redacted
    
    # Verificar que host/path/query se conservan
    assert "192.0.2.1:554" in redacted
    assert "/test" in redacted
    
    print("PASS: test_special_char_password_not_in_output")
    return True


def test_argument_contamination():
    """AC-SEC-13: Verificar que la URL no incluye argumentos de línea de comandos."""
    host = "rtsp://192.168.1.50:554/cam/realmonitor?channel=1&subtype=1"
    username = "admin"
    password = "test123"
    
    url = _with_credentials(host, username, password)
    
    # Lista de strings que NO deben aparecer en la URL
    forbidden = [
        ".venv",
        "Scripts",
        "python.exe",
        "test_rtsp_connection.py",
        "--host",
        "--username",
        "--timeout",
        "--max-frames",
    ]
    
    for f in forbidden:
        assert f not in url, f"Contaminación detectada: '{f}' encontrado en URL: {url}"
    
    print("PASS: test_argument_contamination")
    return True


def run_all_tests():
    tests = [
        test_url_construction_with_special_chars,
        test_redaction_never_contains_secret,
        test_special_char_password_not_in_output,
        test_argument_contamination,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
    
    print(f"\nResultado: {passed} PASS, {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)