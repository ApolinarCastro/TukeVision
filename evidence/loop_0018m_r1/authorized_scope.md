# LOOP-0018M-R1 — AUTHORIZED SCOPE

## Alcance funcional (FASE B — diff quirúrgico)

### `src/capture/live_sources.py` (E01_COMPAT, hash `EEA67E3D…`)
- Ownership: el reader es el ÚNICO dueño de la captura; `cap.release()` SOLO
  en el `finally` del `_reader_loop` (línea 616). `_safe_release` (línea 713)
  se invoca únicamente sobre capturas que NUNCA se entregaron a un reader en
  ejecución (open/reconnect fallidos o instalación cancelada).
- Reconexión acotada: `_reconnect_count` se incrementa una sola vez por intento
  físico (línea 644) y se reinicia SOLO en `__init__` (línea 367). NUNCA se
  reinicia en `_install_capture` (documentado en línea 449).
- Contrato secuencial BASE: cola FIFO acotada `_QUEUE_MAX = 8` con
  backpressure; cada fotograma entregado exactamente una vez, en orden, sin
  latest-wins.

### `src/app/pipeline.py` (hash `9B93EAB0…`)
- Import `SourceState`.
- Detección `source.state == SourceState.FAILED` en bucle y tras el bucle.
- `final_status = "STREAM_LOST"`.
- Sin retail/identity/trajectory/flow.

### `src/ui/controller.py` (hash `CAE5D822…`)
- Solo wiring `rtsp_cfg = config.get("rtsp", {})` + timeouts en `build_source`.
- Sin people/active_tracks/flow/trajectory.

### `config/default.json` (hash `4B1A1E5A…`)
- Solo bloque `rtsp` (open_timeout_ms 8000, read_timeout_ms 4000,
  frame_stall_timeout_s 10.0).

## Invariantes E01_COMPAT (FASE C)

| Invariante | Resultado | Evidencia |
|---|---|---|
| READER_OWNS_CAPTURE | YES | `finally` `_reader_loop` línea 616 |
| SUPERVISOR_RELEASE_DURING_READ | NO | `_shutdown_reader` no llama `release()`; documento líneas 665-676 |
| GLOBAL_RECONNECT_BUDGET_BOUNDED | YES | `_reconnect_count` ++ por intento, límite `_max_reconnect_attempts` |
| RECONNECT_COUNT_NOT_RESET_INTO_INFINITE_FLAPPING | YES | reset solo `__init__` línea 367 |
| SEQUENTIAL_FRAME_CONTRACT_PRESERVED | YES | FIFO `_frame_queue` + backpressure |
| FAILED_SOURCE_REACHES_STREAM_LOST | YES | `read()`→None, `frames()` termina, pipeline detecta FAILED |

FUNCTIONAL_DIFF_SCOPE = PASS