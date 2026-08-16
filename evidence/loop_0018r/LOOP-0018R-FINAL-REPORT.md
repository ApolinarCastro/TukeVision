# LOOP-0018R — REPORTE FINAL: TEMPORAL ACTIVITY + LOCAL TRACKING

## Veredicto

`TEMPORAL_ACTIVITY_LOCAL_TRACKING_OPERATIONAL`

## Resumen

Cuarta capacidad operacional del producto. Sobre la cadena certificada
`CAMERA -> OBSERVATION -> POLICY -> INFERENCE -> EVENT -> EVIDENCE_REFERENCE`
se añadió la conversión de eventos aislados en actividades temporales
coherentes: `EVENT -> LOCAL TRACK -> TEMPORAL ACTIVITY -> OPERATIONAL EVIDENCE`.
Una persona/objeto en CAM-07 inicia una actividad en T0, se mantiene observada
por eventos relacionados, conserva un identificador LOCAL durante su
permanencia, termina en T1 y deja referencias acotadas de evidencia
(first/latest/best). `track_id` es identidad temporal/LOCAL por cámara; NO es
identidad real, NO facial, NO re-ID, NO correlación cross-camera.

## Qué se implementó (`src/temporal/`)

1. `contract.py` — `LocalTrack` (track_id, camera_id, object_type, started_at,
   last_seen_at, status STARTED/ACTIVE/ENDED, event_count, confidence, last_bbox,
   event_refs, evidence_refs first/latest/best) y `TemporalActivity`
   (activity_id, track_id, source_id, activity_type PERSON_PRESENCE/
   OBJECT_PRESENCE, started_at, last_seen_at, ended_at, duration_ms, event_count,
   confidence, evidence_refs). Ambos serializables, sin frames/OpenCV/
   credenciales/estructuras ilimitadas.
2. `tracker.py` — `LocalTracker` (asociación determinista temporal + IoU mínima;
   ciclo STARTED/ACTIVE/ENDED; timeout configurable; nuevo track tras timeout;
   separación de objetos simultáneos por bbox; retención bounded: max_active_tracks,
   max_completed_history, max_event_refs, max_evidence_refs; aislamiento por cámara;
   métricas por cámara/total; close limpio) + `compute_iou` + `build_tracker`.
3. Tests: `test_temporal_tracking.py` (33 deterministas).
4. `config/default.json`: bloque `temporal` (+9 líneas, único cambio de config).

## Reutilización (G6)

- E-02 trajectory: retención acotada + eviction por antigüedad + ciclo
  first_seen/last_seen -> REUSE_WITH_ADAPTATION. Zone/centroid/flow -> NOT_APPLICABLE.
  NO se copió E-02 completo.
- InferenceEvent: consumido por duck-typing (no importado, no modificado).
- `redact_rtsp_url`: REUSE_AS_IS.

## Resultados

- Tests focalizados: 33/33 OK (deterministas).
- Regresión BASE: 359/359 OK (326 baseline + 33 nuevos; 0 regresiones).
- compileall: EXIT=0. Secret leak: 0.
- NEW_DEPENDENCIES=0. E-01/SourceManager/Observation/Inference: intactos.
- Config: diff = solo bloque `temporal` (+9 líneas).

## Restricción de CPU respetada (G26)

LOOP-0018R opera sobre EVENTOS ya generados; no aumenta la frecuencia de
inferencia. QUALITY/BALANCED/ECONOMY vigentes; default BALANCED ~2fps;
continuous 15fps x 4 = NO.

## Próximo PRODUCT ADVANCE (preparado, NO iniciado)

Correlación de trayectorias entre cámaras basada PRIMERO en tiempo/topología/
evidencia, aplicando REUSE BEFORE NEW DEVELOPMENT antes de introducir ReID,
biometría o modelos adicionales.

## Estado

- LOOP-0018R CLOSED (a revisión humana).
- DEC-0036 aprobada (TES/04_Decisions) — contrato arquitectónico nuevo:
  tracking LOCAL temporal/actividad.
- Evidencia completa en `evidence/loop_0018r/`.