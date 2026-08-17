# EXECUTABLE SMOKE TEST — LOOP-0018T

**Fecha:** 2026-08-16 · **Runtime:** BASE `.venv` (3.12.10) · **Objetivo:** `dist\TukeVision`

## Procedimiento

Se ejecutó el flujo equivalente al entry point oficial
(`start_tukevision.ps1` -> `scripts/run_interface.py` -> `UiController` +
`Pipeline`) contra el CÓDIGO EMPAQUETADO en `dist\TukeVision`, usando el runtime
BASE (no portable):

1. Arranque del controlador (`UiController.start("FILE", ...)`) en hilo de trabajo.
2. Procesamiento de 2 fotogramas sintéticos con `FrameSnapshot` entregado al callback.
3. Detención limpia (`StopRequested` -> `final_status=STOPPED_BY_USER`).
4. `controller.close()` (join + limpieza de cola visual).

## Resultado

```
START_STOP_OK status=STOPPED final=STOPPED_BY_USER
EXECUTABLE_SMOKE_OK
```

- OFFICIAL_EXECUTABLE_START = **OK**
- OFFICIAL_EXECUTABLE_CLEAN_SHUTDOWN = **OK**
- OFFICIAL_EXECUTABLE_FUNCTIONAL_CHECK = **OK**
- Sin errores no controlados; shutdown limpio y determinista.

## Nota sobre ejecución GUI física

La prueba se realiza de forma controlada (headless, 2 frames, sin cámara física
ni ventana persistente) para garantizar determinismo y no dejar procesos
abiertos. La GUI Tkinter completa se cubre por `tests/test_ui_controller.py`
(parte de la regresión 370/370).

PHYSICAL_RTSP_EXECUTABLE_CHECK = **NOT_REQUIRED** (G34): la certificación del
paquete no requiere apertura física RTSP; la cadena RTSP (E-01 + SourceManager)
está certificada por sus tests y por la evidencia forense ya archivada (C4). No
se fabrica un resultado de apertura física.

— Fin de executable_smoke_test.md (LOOP-0018T)