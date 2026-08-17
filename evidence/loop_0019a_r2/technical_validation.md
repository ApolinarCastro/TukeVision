# LOOP-0019A-R2 — validación técnica

## Diagnóstico

- `LAST_CONFIRMED_WORKING_STAGE`: `EVIDENCE_RETURNED`
- `FIRST_BROKEN_STAGE`: `UI_MODEL_RECEIVED`
- Causa raíz: el wrapper consultaba `event.detections` en vez del conteo
  canónico `event.metadata["detections"]`, y el estado latest-wins del video
  sobrescribía inmediatamente la analítica sparse con valores vacíos.
- Segundo pipeline: no creado.
- Núcleo protegido (`src/app`, `src/inference`, `src/temporal`,
  `src/behavior`, `src/evidence`): sin cambios R2.

## Reparación

- Adaptación única del resultado canónico a presentación.
- Video latest-wins conservado; último resultado analítico real retenido por cámara
  con `analytics_frame_index` explícito.
- Traza bounded: diez contadores y último frame por cámara; no conserva frames,
  URLs, credenciales ni texto libre.
- STOP derivado del estado real del runtime multicámara.
- Controles FILE/WEBCAM/RTSP legacy ocultos en modo multicámara.
- Botón Evidencia conectado a `config.evidence.root` (`data/runtime_evidence`).
- Letterbox de 420×245 por panel, conservando aspecto y sin upscaling.

## Gates ejecutados

| Gate | Resultado | Evidencia |
|---|---|---|
| Baseline | PASS | 423 tests, 4 skips |
| RED focalizado | PASS como reproducer | fallo `0 != 2` + import del adaptador ausente |
| GREEN focalizado | PASS | 10 tests |
| Full regression | PASS | 428 tests, 4 skips, 24.507 s |
| Compileall | PASS | `python -m compileall -q src scripts tests` |
| Diff check | PASS | sin errores whitespace |
| Secret scan | PASS | sólo variable `password` alimentada por `getpass`; sin valor literal |
| Protected core | PASS | diff R2 vacío en capas protegidas |

Los cuatro skips corresponden al backend real opcional del fixture existente;
no son regresiones R2.

## Gate pendiente

El launcher real `TukeVision.bat` debe permanecer abierto para G1–G10. Ningún
gate de operador se autoaprueba desde tests.
