# LOOP-0018R — Resultados de tests

Fecha: 2026-08-16
Intérprete: portable `.venv` (Python 3.12.10; ultralytics 8.4.115; cv2 5.0.0)

## Tests focalizados — deterministas (`tests/test_temporal_tracking.py`)

Comando: `python -m unittest tests.test_temporal_tracking -v`

Resultado: **33/33 OK** (0.003 s)

Cobertura:

- Contrato LocalTrack (creación, validación, serialización roundtrip, immutabilidad
  de datos vía to_dict/from_dict).
- Contrato TemporalActivity (serialización roundtrip).
- `duration_ms` y timestamps UTC inválidos.
- IoU (básica, sin área).
- Continuidad conceptual obligatoria: CAM-07 PERSON_DETECTED @ T0, T0+1s, T0+2s ->
  UN solo track, UNA actividad, event_count=3 (G8/G9/G14/G15).
- STARTED (1er evento) -> ACTIVE (actualización en ventana).
- Cierre por timeout (G12) y nuevo track tras timeout (G13, no resucita).
- Ventana superada -> cierre del anterior + nuevo track.
- Independencia de IDs por cámara (G7).
- Cuatro cámaras lógicas aisladas con eventos intercalados (G16) y sin
  contaminación cross-camera (G17).
- Dos personas espacialmente separadas en CAM-07 -> dos tracks (G10/G11).
- Actualización por bbox IoU -> mismo track.
- Eventos incompatibles (PERSON vs OBJECT) no mezclados.
- Evidencia first/latest/best (G18); sin fabricación de paths (G19).
- Retención acotada: event refs bounded, completed history bounded, active tracks
  bounded (G20/G21/G22).
- Error isolation (G23): evento inválido de CAM-03 no afecta CAM-01/05/07.
- Configuración inválida -> TemporalConfigError (G25); build_tracker config-driven.
- Métricas operativas (G24): events_received/tracks_started/updated/ended/
  activities_started/ended.
- Determinismo: mismas entradas -> mismas salidas (G9).
- Secret leak = 0 (redact en serialización) (G29).

## Regresión completa

Comando: `python -m unittest discover -s tests -p "test_*.py"`

Resultado: **359/359 OK** (24.8 s)

- Baseline heredado: 326/326.
- Nuevos: 33.
- Regresiones: 0 (G31/G32).

## Compilación

`python -m compileall -q src tests` -> EXIT=0 (`COMPILEALL_OK`).

## Demo funcional con InferenceEvent real

Consumido `InferenceEvent` (duck-typing) sobre un track con 3 eventos
PERSON_DETECTED (conf 0.6/0.9/0.8) y evidence EVID-1/2/3:

- TRACK: `TRK-CAM-07-000001`, status ACTIVE, event_count 3, confidence 0.9,
  event_refs [E1,E2,E3], evidence_refs first=EVID-1/latest=EVID-3/best=EVID-2.
- ACTIVITY: `ACT-CAM-07-000001`, PERSON_PRESENCE, event_count 3,
  evidence_refs best=EVID-2 (correcto).
- METRICS CAM-07: events_received 3, tracks_started 1, tracks_updated 2,
  association_misses 0, errors 0.