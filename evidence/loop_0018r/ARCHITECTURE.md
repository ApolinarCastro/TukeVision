# LOOP-0018R — Arquitectura y contratos mínimos

Fecha: 2026-08-16

## Flujo

```
CAMERA -> OBSERVATION -> POLICY -> INFERENCE -> EVENT -> LOCAL TRACK
        -> TEMPORAL ACTIVITY -> OPERATIONAL EVIDENCE
```

- La cadena CAMERA..EVENT permanece intacta (LOOP-0018Q). LOOP-0018R añade:
  `EVENT -> LOCAL TRACK -> TEMPORAL ACTIVITY -> OPERATIONAL EVIDENCE`.
- `LocalTracker.ingest(event, bbox=None)` consume `InferenceEvent` por duck-typing
  (no importa la capa de inferencia; no modifica su contrato).

## Contratos (`src/temporal/contract.py`)

### LocalTrack
Campos mínimos: `track_id`, `camera_id` (source_id), `object_type`, `started_at`,
`last_seen_at`, `status` (STARTED/ACTIVE/ENDED), `event_count`, `confidence`,
`last_bbox` (opcional), `event_refs` (acotadas), `evidence_refs`
(first/latest/best). Serializable (to_dict/from_dict), sin frames, sin OpenCV,
sin credenciales (redact_rtsp_url), refs acotadas.

Identidad: `TRK-<CAMERA>-<SEQ>` por cámara (espacio de IDs independiente por
cámara). NO identidad real; NO facial; NO cross-camera.

### TemporalActivity
Campos mínimos: `activity_id` (`ACT-<CAMERA>-<SEQ>`), `track_id`, `source_id`,
`activity_type` (PERSON_PRESENCE/OBJECT_PRESENCE), `started_at`, `last_seen_at`,
`status`, `ended_at` (opcional), `duration_ms`, `event_count`, `confidence`,
`evidence_refs`. Serializable. NO clasifica comportamiento (robo/sospecha/
intención/amenaza son capas posteriores).

## Motor (`src/temporal/tracker.py`)

- `LocalTracker`: estado por cámara aislado (`_cameras[camera_id]`), sin memoria
  compartida entre cámaras.
- `compute_iou`: IoU mínima para asociación espacial cuando hay bbox.
- Ciclo de vida: STARTED (primer evento) -> ACTIVE (actualización en ventana) ->
  ENDED (timeout o cierre).
- Asociación determinista `_find_candidate`: mismo `object_type`, dentro de
  `association_window_ms`, y si bbox presente, IoU >= `iou_threshold` (mayor IoU
  gana). Sin bbox: el más reciente dentro de la ventana (temporal, determinista).
- Cierre por timeout `_close_expired`: gap > `track_timeout_ms` -> ENDED.
- Nuevo track tras timeout `_start_track`: NO resucita el anterior.
- Separación de objetos simultáneos: bbox distintos -> IoU baja -> tracks
  distintos (mismo `object_type` dentro de la ventana).
- Retención acotada: `max_active_tracks` (evict oldest), `max_completed_history`
  (FIFO acotado), `max_event_refs` (últimos N), `max_evidence_refs` (<=3).
- Aislamiento por cámara: `ingest` envuelve la asociación en try/except;
  error de CAM-X -> `errors`+1, no afecta CAM-Y.
- Métricas por cámara y total: events_received, tracks_started, tracks_updated,
  tracks_ended, activities_started, activities_ended, association_misses, errors.
- `close()`: cierra todos los tracks activos (ENDED) y devuelve totales.

## Estrategia de evidencia operacional (first/latest/best)

Solo se conservan `evidence_reference` existentes; NUNCA se fabrican paths.
- first: primera evidencia observada.
- latest: la más reciente.
- best: la del evento con mayor confidence (empate: primera).
La confianza de referencia se trackea por contrato (track vs activity) para no
compartir estado.

## Configuración (`config/default.json` -> `temporal`)

- `association_window_ms` (2000), `track_timeout_ms` (5000),
  `iou_threshold` (0.05), `max_active_tracks` (8),
  `max_completed_history` (32), `max_event_refs` (16), `max_evidence_refs` (3).
- Config inválida -> `TemporalConfigError` explícito (fail-safe, nunca silencio
  peligroso). Sin bloque -> defaults conservadores documentados.
- `build_tracker(config)` valida y construye.

## Frame budgeting

LOOP-0018R opera sobre EVENTOS ya generados. NO aumenta la frecuencia de
inferencia. QUALITY/BALANCED/ECONOMY permanecen vigentes. Default BALANCED
~2fps; continuous 15fps x 4 = NO.

## Invariantes

- CROSS_CAMERA_IDENTITY_CORRELATION = NO (G17).
- NO_FACIAL / NO_REID / NO_BIOMETRICS = NO introducidos.
- BOUNDED_RETENTION = YES (event refs, completed history, active tracks,
  evidence refs).
- NO_FRAME_STORAGE = YES (solo refs; evidencia por referencia).
- NO_NEW_DEPENDENCIES = YES (stdlib).
- NO_PERSISTENT_STORAGE = YES (in-memory bounded; sin SQLite/Redis/vector DB).