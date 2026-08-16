# LOOP-0018R — Mapa de reuso (G6: REUSE BEFORE NEW DEVELOPMENT)

Fecha: 2026-08-16

## E-02 Trajectory — evaluación enfocada (NO auditoría general)

Fuente portable: `src/retail/trajectory.py` (TrajectoryPoint, TrackTrajectory,
FlowCounter, TrajectoryStore).

| Pieza E-02 | Clasificación | Uso en LOOP-0018R |
|---|---|---|
| Retención acotada (`max_tracks`, `max_points_per_track`) | REUSE_WITH_ADAPTATION | Patrón adoptado: `max_active_tracks`, `max_completed_history`, `max_event_refs` (eviction del más antiguo). |
| Eviction del track más antiguo (`min(first_seen)`) | REUSE_WITH_ADAPTATION | `_evict_oldest_active` + `completion_order` FIFO acotado. |
| Ciclo de vida track (`first_seen`/`last_seen`, add_point) | REUSE_WITH_ADAPTATION | `started_at`/`last_seen_at` + `event_count` en `LocalTrack`. |
| `zone_id`/`dwell_seconds`/`centroid` | NOT_APPLICABLE | Retail/geo-específico; datos no disponibles en eventos LOOP-0018Q. |
| `FlowCounter` (entries/exits/inside) | NOT_APPLICABLE | Lógica de flujo/zona, fuera de alcance de tracking temporal local. |
| `get_zone_history` | NOT_APPLICABLE | Sin zonas en la cadena EVENT->TRACK->ACTIVITY. |

Conclusión: **NO se copia E-02 completo**. Solo se adapta el patrón de retención
acotada y eviction por antigüedad, manteniendo trazabilidad origen->adaptación.

## Reuso directo (REUSE_AS_IS / REUSE via CONSUMPTION)

| Origen | Uso |
|---|---|
| `src/inference/events.py::InferenceEvent` | Consumido por duck-typing (`ingest(event)`); NO importado, NO modificado. |
| `src/observability/logging_setup.py::redact_rtsp_url` | Sanitización en `LocalTrack.to_dict`/`TemporalActivity.to_dict`. |
| `config/default.json` | Bloque `temporal` añadido; resto intacto. |

## No aplicable / NO migrado (no abrir)

- E-03 Identity/ReID: NO (requiere DEC-0013; prohibido en este loop).
- E-04 Command Center UI: NOT_APPLICABLE (sin GUI).
- E-05 Quality engine: NO REVISADO (no se abre; sin interfaz necesaria).

## Verificación de no-reescritura

- `src/capture/live_sources.py` (E-01): INTACTO (`6a9ae7e…`).
- `src/capture/source_manager.py`: INTACTO (`29e0274…`).
- `src/observations/activity.py`: INTACTO (`114b6a…`).
- `src/inference/*`: INTACTO (hashes LOOP-0018Q).
- `src/temporal/*`: NUEVO (solo stdlib).
- NEW_DEPENDENCIES = 0.