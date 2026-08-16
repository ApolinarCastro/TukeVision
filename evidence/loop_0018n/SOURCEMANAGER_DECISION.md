# LOOP-0018N — SOURCEMANAGER_DECISION (PASO 6)

## ¿Existe SourceManager?

- **BASE:** NO. Búsqueda `class SourceManager|SourceRegistry` → 0 coincidencias.
- **PORTABLE:** NO. Mismo resultado.
- **Parcialmente:** el candidato a SourceManager se puede componer de piezas existentes:
  - `src/capture/live_sources.py` — `RTSPSource` (E01_COMPAT certificado: open/read/stall/reconnect, state, health).
  - `src/capture/rtsp_url.py` — canal 1-16 + subtype + normalización `/cam/realmonitor` (C-01/C-02 certificados).
  - `src/app/pipeline.py` — `Pipeline.process_source()` unicámara.
  - `src/ui/controller.py` — `build_source()` (wiring RTSP timeouts).
  - `src/capture/quality_engine.py` (E-05 portable) — decisión subtype main/sub.

## Decisión

**CAN_BE_EXTRACTED_AS_SMALL_ADAPTER** (composición, NO desarrollo desde cero).

Un `SourceManager` nuevo y pequeño (~1 archivo) que componga las piezas existentes:
register_source / start / stop / restart / health / snapshot / list_sources / isolate_failure.
Ninguna lib nueva. Reutiliza RTSPSource, rtsp_url y Pipeline por cámara.

## Contrato mínimo (API)

```text
register_source(camera) -> camera_id          # valida y registra descriptor de cámara
start(camera_id)        -> None                # lanza hilo de captura+pipeline por cámara
stop(camera_id)         -> None                # detiene limpio esa cámara
restart(camera_id)      -> None                # stop + start
health(camera_id)       -> CameraHealth         # state, fps, resolution, last_frame_age, reconnect_state, queue, detections, tracks, zone_state, event_count
snapshot(camera_id)     -> dict                 # frame reciente + metadatos
list_sources()          -> List[CameraDescriptor]
isolate_failure(camera_id) -> None             # garantiza que una cámara fallida no afecta a las demás
```

## Escalado (1 → 4 → 8 → 16)
- API idéntica para cualquier N: `register_source` + `start` + `health`/`snapshot`.
- El escalado real está limitado por recursos (PASO 8), no por la API.
- `_QUEUE_MAX` por cámara (E01) y backpressure garantizan aislamiento.
- Namespace de track_id por cámara (cada cámara con su Pipeline) → sin colisiones cross-camera.

## SOURCEMANAGER_DECISION = COMPLETE (G5)
- Estado: **REQUIRES_SMALL_NEW_ADAPTER** (composición de piezas certificadas).
- NO se reescribe nada de E-01. NO se migra E-02..E-05.