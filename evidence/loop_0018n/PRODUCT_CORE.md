# LOOP-0018N — PRODUCT CORE (PASO 5) — especificación, NO implementación

Pipeline objetivo reutilizando la arquitectura canónica (`ARCHITECTURE.md`). No es una segunda
arquitectura: es la especialización multicámara del flujo existente.

## Pipeline objetivo

```text
CAMERAS
  -> SourceManager            (orquestación, registro, aislamiento)
  -> PerCameraHealth          (state, fps, resolution, last_frame_age, reconnect_state, queue, event_count)
  -> PerCameraCapture         (RTSPSource E01_COMPAT, cola FIFO acotada + backpressure)
  -> PerCameraDetection       (YOLO11n, config-driven por cámara)
  -> PerCameraTracking        (ByteTrack por cámara, namespace de track_id)
  -> Trajectory               (E-02 TrajectoryStore por cámara)
  -> Zone / Dwell / Flow      (zona poligonal, permanencia, IN/OUT/INSIDE)
  -> Interaction              (Activity Layer, taxonomía)
  -> Activity                 (Activity Layer, post-evento)
  -> Event                    (motor de eventos)
  -> Risk                     (calculador de riesgo)
  -> Evidence                 (almacén inmutable)
  -> CommandCenter            (UI grid, snapshot por cámara)
```

## Invariante crítico

**Una cámara fallida NO puede derribar las demás.**
- Aislamiento por hilo: cada cámara corre su propio hilo de captura+pipeline.
- `SOURCE_ISOLATION=YES`, `ONE_CAMERA_FAILURE_DOES_NOT_STOP_OTHERS=YES`.
- `NO_SHARED_MUTABLE_CAPTURE=YES` (nada compartido entre cámaras).
- Cola acotada por cámara (`_QUEUE_MAX`) + backpressure.

## Estado mínimo por cámara (obligatorio)

```text
camera_id          # identificador 1..16 / string
channel            # canal RTSP 1-16
subtype            # 0 (main) / 1 (sub)
source_state       # CONNECTING/OPEN/STALLED/RECONNECTING/FAILED/CLOSED
health             # booleano/agregado
fps                # medido
resolution         # WxH
last_frame_age     # monotónico
reconnect_state    # budget global E01, no reiniciado
detections         # últimas detecciones
tracks             # tracks activos
zone_state         # estado de zona de la cámara
event_count        # contador de eventos
```

## Origen de cada componente

| Componente | Origen | Estado |
|---|---|---|
| SourceManager | NUEVO (adapter) | DISEÑADO |
| PerCameraHealth | E01 (state/health props) + adapter | DISEÑADO |
| PerCameraCapture | `RTSPSource` (E01_COMPAT) | EXISTE CERTIFICADO |
| PerCameraDetection | `PersonDetector` (YOLO11n) | EXISTE CERTIFICADO |
| PerCameraTracking | `PersonTracker` (ByteTrack) | EXISTE CERTIFICADO |
| Trajectory | E-02 portable | REUTILIZABLE (adaptación) |
| Zone/Dwell/Flow | `Zone` + E-02 FlowCounter | EXISTE + REUTILIZABLE |
| Interaction/Activity | NUEVO (Activity Layer) | DISEÑADO |
| Event/Risk/Evidence | motores existentes | EXISTE CERTIFICADO |
| CommandCenter | E-04 portable | REUTILIZABLE (adaptación) |

## Nota
E-01..E-05 no se migran aquí. Solo se define el destino de cada pieza.