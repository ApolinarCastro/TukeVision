# HOTFIX-RTSP-001 — Protección de credenciales y stderr en RTSP

## EXECUTION_ID

HOTFIX-RTSP-001

## Alcance

Backport del hotfix RTSP desde el portable experimental validado
físicamente contra infraestructura CCTV autorizada (LOOP-0012C-R).

## Causa raíz confirmada

1. **Construcción de URL**: `_with_credentials` en
   `scripts/test_rtsp_connection.py` codifica correctamente usuario y
   contraseña con `urllib.parse.quote`. Sin hallazgos.
2. **Fuga de credenciales vía stderr de FFmpeg**: el backend FFmpeg de
   OpenCV escribe directamente en el descriptor 2 (stderr nativo) a nivel
   C, eludiendo `sys.stderr` de Python y el sistema de logging. Ante un
   fallo de conexión RTSP, FFmpeg puede emitir la URL completa (con
   credenciales) a stderr.
3. **metadata.path**: `RTSPSource` usaba `"rtsp://[redacted]"` hardcodeado,
   perdiendo host/path/query útiles para diagnóstico.

## Cambios aplicados

### src/capture/live_sources.py

- Añadido `_suppress_native_stderr()`: context manager que duplica fd 2,
  lo redirige a `os.devnull` y lo restaura siempre mediante `try/finally`
  (incluso ante excepción). Afecta únicamente a operaciones RTSP; no se
  aplica globalmente.
- Añadido `_create_capture_with_suppressed_stderr()`: helper que envuelve
  la creación de VideoCapture suprimiendo stderr nativo.
- `OPENCV_FFMPEG_LOGLEVEL=quiet` a nivel de módulo (defensa complementaria,
  no sustituto de la protección de fd 2).
- `RTSPSource.open()`, `RTSPSource.read()` y `RTSPSource._reconnect()`
  usan la supresión de stderr. La semántica de reconexión certificada no
  cambió.
- `metadata.path` ahora usa `redact_rtsp_url(self._rtsp_url)` (función
  canónica de `src/observability/logging_setup.py`).

### test_rtsp.ps1 (nuevo)

Launcher que localiza `.venv\Scripts\python.exe`, ejecuta
`scripts\test_rtsp_connection.py` reenviando argumentos y propaga el exit
code. Sin credenciales, sin IP, sin rutas absolutas.

### tests/test_secret_leak.py (nuevo)

17 pruebas permanentes de no exposición de secretos: AC-SEC-01 a
AC-SEC-14 y ARGUMENT_CONTAMINATION_TEST, usando exclusivamente
credenciales ficticias y el canary `SECRET_CANARY_RTSP_8F21`.

## Verificación

- Suite completa: 220 pruebas aprobadas.
- `PROTECTED_CORE_CHANGED: NO`.
- `BUSINESS_LOGIC_CHANGED: NO`.
- `DEPENDENCIES_CHANGED: NO`.
- `COMPILE_CHECK: PASS`.
- `PIP_CHECK: PASS`.
- `GIT_DIFF_CHECK: PASS`.
- Escaneo de secretos: sin IP real, sin credenciales reales persistidas.

## Compromisos

- `REAL_RTSP_INPUT_STATUS: FORMALLY_CERTIFIED` (30 frames, 352x240,
  4.24 FPS, fuente cerrada correctamente).
- `REAL_CAMERA_VISION_PIPELINE: PENDING`.
- `UC001_OPERATIONAL_VALIDATION: BLOCKED_BY_OPERATIONAL_INPUT`.

## Nota de seguridad

Este documento no contiene IP, usuario ni contraseña reales. La evidencia
física del portable experimental se conserva separada (decisión humana).
