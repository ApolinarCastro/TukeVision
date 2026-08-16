# LOOP-0018R — Determinismo, aislamiento, retención, ciclo de vida y evidencia

Fecha: 2026-08-16

## Determinismo (G9)

Dos ejecuciones idénticas (3 eventos PERSON_DETECTED @ T0, T0+1s, T0+2s, conf
0.85/0.9/0.6, evidence R1/R2/R3):

```
DETERMINISM_SAME = True
result = ('TRK-CAM-07-000001', 3, 'ACTIVE', 'EV2', ('E1','E2','E3'))
```

Mismas entradas -> mismo track_id, event_count, status, best-evidence y
event_refs. PASS.

## Aislamiento entre cámaras (G16/G17)

4 cámaras lógicas, eventos intercalados por ronda (4 rondas):

```
FOUR_CAM_IDENTIFIERS  = ['TRK-CAM-01-000001', 'TRK-CAM-03-000001', 'TRK-CAM-05-000001', 'TRK-CAM-07-000001']
FOUR_CAM_DISTINCT     = True
FOUR_CAM_EVENT_COUNT  = [4, 4, 4, 4]
```

- IDs independientes y únicos por cámara (espacios de IDs separados).
- Cada cámara acumula SOLO sus 4 eventos (sin contaminación cross-camera).
- No existe correlación de identidad entre cámaras (G17 = NO). PASS.

## Ciclo de vida y timeout (G8/G12/G13)

`association_window_ms=2000`, `track_timeout_ms=5000`:

```
LIFECYCLE_AFTER_1ST          = STARTED   (1er evento)
LIFECYCLE_AFTER_2ND          = ACTIVE    (actualización en ventana)
BEFORE_TIMEOUT_TRACKS        = 1
AFTER_TIMEOUT_ACTIVE_TRACKS  = 1         (nuevo track)
AFTER_TIMEOUT_NEW_TRACK_EVENT_COUNT = 1  (solo el evento nuevo)
COMPLETED_OLD_TRACK_STATUS   = ENDED
COMPLETED_OLD_TRACK_EVENT_COUNT = 2      (T1,T2 conservados en el viejo)
```

Evento a T0+7s (fuera de ventana 2s y de timeout 5s): el track previo se cierra
(ENDED, event_count=2) y se crea UN NUEVO track (event_count=1). No hay
resurrección silenciosa. PASS.

## Retención acotada (G20/G21/G22)

`max_active_tracks=3`, `max_completed_history=2`, `max_event_refs=4`:

```
BOUNDED_COMPLETED_LEN   = 2                       (<= max_completed_history=2)
BOUNDED_COMPLETED_IDS   = ['TRK-CAM-02-000004', 'TRK-CAM-02-000005']  (FIFO, los más recientes)
BOUNDED_EVENT_REFS_LEN  = 2                       (<= max_event_refs=4)
```

Historial de completados acotado por los N más recientes; event_refs acotadas a
las últimas N. Active tracks acotados por `max_active_tracks` (evict oldest,
verificado en test unitario). PASS.

## Aislamiento de errores (G23)

Evento con timestamp inválido de CAM-03:

```
ERROR_ISOLATION_EXC         = TemporalValidationError
ERROR_ISOLATION_CAM01_TRACKS = 1   (CAM-01 no afectada)
ERROR_ISOLATION_METRICS     = 1    (errors+=1 en CAM-03)
ERROR_ISOLATION_CAM05_ZERO  = 0    (CAM-05 intacta)
```

El error de CAM-03 incrementa `metrics.errors` de CAM-03 y NO afecta CAM-01/05/07.
PASS.

## Estrategia de evidencia (G18/G19)

Demo funcional con 3 eventos (conf 0.6/0.9/0.8, evidence EVID-1/2/3):

```
TRACK:  event_refs [E1,E2,E3]; evidence_refs first=EVID-1 latest=EVID-3 best=EVID-2
ACTIVITY: evidence_refs best=EVID-2
```

- first = primera observada; latest = la más reciente; best = máxima confidence
  (0.9 -> EVID-2), con empate conservando la primera.
- La confianza de referencia se trackea por contrato (track vs activity) para
  que ambas actividades reporten el mejor evento correctamente.
- Solo se conservan `evidence_reference` EXISTENTES; nunca se fabrican paths.
  (Test `test_evidence_no_fabricated_paths`: evento sin evidence_ref -> refs None.)
PASS.