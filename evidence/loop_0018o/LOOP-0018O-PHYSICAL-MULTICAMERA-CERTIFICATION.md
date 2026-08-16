# LOOP-0018O — VALIDACIÓN FÍSICA MULTICÁMARA (4 cámaras reales)

## VEREDICTO

`MULTICAMERA4_PHYSICAL_CERTIFIED`

## Resumen

Primera demostración tangible de la arquitectura operacional: **4 cámaras RTSP
reales simultáneas** administradas por el SourceManager certificado (LOOP-0018N),
sobre el mismo DVR autorizado y certificado de loops anteriores.

## Infraestructura física

- DVR: `186.103.177.83:554` (mismo DVR certificado en LOOP-0018L/M).
- Usuario: `admin` (contraseña solo en memoria, getpass; no persistida).
- Detección pasiva: **16/16 canales accesibles** (subtype=1, 352x240@7fps).
- Selección: **CAM-07** (subtype=0, 1280x720@15fps — referencia certificada
  LOOP-0018L) + CAM-01/03/05 (subtype=1, 352x240@7fps).
- BASE: branch `product/loop-0018n-multicamera4`, commit `ccb3b2a`.

## Fases y resultados (harness `validate_multicamera4.py`, 300 s)

| Fase | Criterio | Resultado |
|---|---|---|
| 0 | Precheck (base, procs, dumps) | PASS |
| 1 | Detección pasiva canales 1-16 | PASS (16/16 accesibles) |
| 2 | Selección 4 cámaras (incl. CAM07) | PASS (7,1,5,3) |
| 3 | Start simultáneo | PASS |
| 4 | Simultaneidad (4 healthy + frames) | PASS |
| 5 | Estabilidad 300 s (0 stalls/reconnects) | PASS |
| 6 | Aislamiento stop CAM-03 (otras intactas) | PASS |
| 6b | Restart CAM-03 (otras intactas) | PASS |
| 7 | Salud individual | PASS (4 cámaras) |
| 8 | Shutdown limpio (close_all, tcp554=0) | PASS |
| 9 | Certificación | **CERTIFIED** |

## Consumo de recursos (muestreo 5s, 61 muestras, PID 23860)

| Métrica | Valor |
|---|---|
| RAM proceso | 227.8 → 232.4 MB (estable, **sin fuga**: +4.6 MB en 300 s) |
| Conexiones TCP :554 | **4 simultáneas** sostenidas |
| Threads | 9 estables |
| Handles | 574-577 estables |
| Frames entregados (CAM-07) | 4594 en 300 s (~15 fps sostenido) |
| Frames entregados (CAM-01/03/05) | ~2090-2160 cada una (~7 fps) |
| FRAME_STALL_DETECTED | **0** |
| RECONNECT_ATTEMPT (>1) | **0** |
| CrashDumps nuevos | **0** (baseline 0 → post 0) |

## Aislamiento (secuencia del objetivo)

- **Detener una (CAM-03) sin afectar las demás:** CAM-07/01/05 continuaron
  entregando frames sin interrupción (4667→4722, 2201→2225, 2122→2148
  durante la ventana de stop). CAM-03 quedó REGISTERED (no healthy).
- **Reiniciar CAM-03:** volvió a OPEN con frames; las otras 3 intactas.
- Confirmado `SOURCE_ISOLATION=YES` y `ONE_CAMERA_FAILURE_DOES_NOT_STOP_OTHERS=YES`
  sobre cámaras reales.

## Salud individual final (FASE 7)

| Cámara | Estado | Resolución | FPS | Frames | Stall | Cola |
|---|---|---|---|---|---|---|
| CAM-07 | OPEN | 1280x720 | 15.0 | 4797 | 0 | 8 |
| CAM-01 | OPEN | 352x240 | 7.0 | 2260 | 0 | 8 |
| CAM-05 | OPEN | 352x240 | 7.0 | 2183 | 0 | 8 |
| CAM-03 | OPEN | 352x240 | 7.0 | 16 (tras restart) | 0 | 8 |

## Precisión de evidencia (NO se declara)

- NO se ejecutó YOLO/ByteTrack en esta validación (captura + orquestación).
  La detección por cámara es config-driven (hallazgo LOOP-0018N: 54.5 ms/frame).
- NO se provocó reconnect físico (estabilidad natural, sin stalls) — no aplica.
- NO 8/16 cámaras simultáneas (solo 4, conforme al plan).
- NO Activity Layer, IA, refactor, limpieza del portable ni integraciones nuevas.

## Evidencia generada

`evidence/loop_0018o/`: precheck.json, channel_detection.json, selection.json,
start_events.json, simultaneity.json, resource_samples.csv (61 muestras),
stability_events.jsonl, isolation_stop.json, isolation_restart.json,
final_health.json, shutdown.json, certification.json, validate_multicamera4.py,
console_output.txt.

## Próximo paso

El frente multicámara básico queda cerrado. Avance inmediato al siguiente
PRODUCT ADVANCE según la regla de salida definida por el operador.