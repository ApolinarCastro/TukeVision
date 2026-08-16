# LOOP-0018N — FIRST_PRODUCT_DELIVERY (PASO 7)

## Decisión

**FIRST_PRODUCT_DELIVERY = REAL_MULTICAMERA_4_CAMERAS** (prioridad preferida, sin dependencia bloqueante demostrada).

## Resultado observable

1. 4 cámaras reales simultáneas (4 `RTSPSource` activos).
2. 4 estados independientes (per-camera state: CONNECTING/OPEN/STALLED/RECONNECTING/FAILED/CLOSED).
3. 4 feeds reales (per-camera frame routing, cola FIFO acotada).
4. Cada cámara con health propio (fps, resolución, last_frame_age, reconnect_state, detections, tracks).
5. Fallo de una NO derriba las demás (SOURCE_ISOLATION).
6. Command Center muestra estado real (snapshot por cámara disponible para la UI).
7. YOLO/ByteTrack pueden activarse por cámara según presupuesto definido (config-driven).

## Alcance dentro de este LOOP (si gate PASO 11 lo permite)

- `SourceManager` (mínimo, API del contrato) + `CameraDescriptor` + `CameraHealth`.
- Tests sintéticos deterministas de lifecycle (PASO 14) ANTES de prueba física.
- SIN Activity Layer, SIN ReID, SIN segmentación, SIN web API, SIN E-02..E-05.

## Fuera del alcance (explícito)

- 8/16 cámaras (NO antes de certificar 4).
- Migración automática de E-02..E-05.
- Introducción de frameworks nuevos.
- Modificación de OpenCV/FFmpeg/E-01.

## PRIORITY CONFIRMADA = REAL_MULTICAMERA_4_CAMERAS (G6)

Dependencia bloqueante: NINGUNA demostrada (SourceManager compone piezas certificadas).