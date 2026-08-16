# LOOP-0018N — IMPLEMENTATION_SCOPE (PASO 12-14)

## Qué se implementó (mínimo autorizado por operador)

**Branch:** `product/loop-0018n-multicamera4` (desde `ccacb3d95f963a973ff64400cbdb88500dbde705`).

| Archivo | Acción | Detalle |
|---|---|---|
| `src/capture/source_manager.py` | NUEVO | SourceManager mínimo: CameraDescriptor, CameraHealth, _CameraRuntime, SourceManager. Compone RTSPSource E01_COMPAT + rtsp_url.build_rtsp_url. 0 dependencias nuevas. |
| `tests/test_source_manager.py` | NUEVO | 14 tests sintéticos deterministas con FakeSource (sin cámaras reales). |

## Invariantes verificados por los tests

| Invariante | Estado | Test |
|---|---|---|
| SOURCE_ISOLATION (fallo no detiene a las demás) | PASS | test_one_camera_failure_does_not_stop_others, test_isolate_failure_keeps_others, test_frames_failed_midstream_isolated |
| PER_CAMERA_STATE (health por cámara) | PASS | test_start_health_snapshot, test_health_type |
| ONE_FAILURE_DOES_NOT_STOP_OTHERS | PASS | idem aislamiento |
| NO_SHARED_MUTABLE_CAPTURE (una FakeSource por cámara) | PASS | test_three_more_cameras_parallel |
| Namespacing camera_id/track_id (cola por cámara) | PASS | test_register_and_list_sources, test_three_more_cameras_parallel |
| BOUNDED_QUEUE (FIFO acotada drop-oldest) | PASS | test_bounded_queue_drop_oldest |
| CLEAN_START_STOP (stop limpio y aislado) | PASS | test_stop_is_clean_and_isolated, test_restart |
| CLEAN_SHUTDOWN (close_all) | PASS | todos los tests cierran con close_all |
| SECRET_LEAK=0 (password no expuesto) | PASS | test_secret_not_exposed_in_inventory + grep manual |
| E-01 INTACTO (RTSPSource no modificado) | PASS | git diff solo toca source_manager.py + test |

## API expuesta (contrato SOURCEMANAGER_DECISION.md)

register_source / start / stop / restart / health / snapshot / list_sources / isolate_failure / close_all.

## Validación

- Tests sintéticos: **14/14 OK** (3 corridas deterministas → 3/3 OK).
- Regresión BASE: **241/241 OK** (227 previos + 14 nuevos; 24.1 s).
- `python -m compileall -q src` → **EXIT=0**.
- Secret scan: 0 exposiciones.

## NO implementado (explícito, dentro del alcance mínima)
- Activity Layer, ReID/E-03, E-02/E-04/E-05, segmentación, web API, 8/16 cámaras, GPU, ONVIF/PTZ.
- Modificación de E-01/OpenCV/FFmpeg. Sin dependencias nuevas.