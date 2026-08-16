# LOOP-0018Q — Demostración funcional (backend real YOLO)

Fecha: 2026-08-16

## Procedimiento

Pipeline construido vía `build_pipeline(cfg)` (config-driven, bloque `inference`),
cámara lógica `CAM-07`, 4 feeds a 15fps con la imagen real `data/temp/zidane.jpg`
(contiene personas). Política BALANCED ~2fps -> solo el frame 0 se procesa.

## Métricas de cámara

```json
{
  "considered": 4,
  "processed": 1,
  "skipped_by_policy": 3,
  "inference_errors": 0,
  "events_generated": 1,
  "latency_ms_sum": 1319.218,
  "latency_ms_last": 1319.218,
  "latency_ms_avg": 1319.218,
  "profile": "BALANCED",
  "queued_events": 1,
  "event_queue_dropped": 0
}
```

## Totales

```json
{"considered": 4, "processed": 1, "skipped_by_policy": 3, "inference_errors": 0, "events_generated": 1, "latency_ms_sum": 1319.218, "latency_ms_last": 1319.218, "latency_ms_avg": 1319.218}
```

## Evento generado

```json
{
  "event_id": "EVT-CAM-07-000001",
  "camera_id": "CAM-07",
  "timestamp": "2026-08-16T21:34:01.732010Z",
  "event_type": "PERSON_DETECTED",
  "confidence": 0.8404608964920044,
  "producer": "yolo:person_detector",
  "model": "models/yolo11n.pt",
  "observation_ref": null,
  "inference_ref": "INF-CAM-07-000001",
  "evidence_ref": null,
  "metadata": {"detections": 2, "engine": "yolo"}
}
```

## Lectura

- Frame budgeting REAL: 4 frames considerados, 1 procesado (política BALANCED),
  3 saltados por política. Sin inferencia continua.
- Backend real operativo: 2 detecciones de persona en `zidane.jpg`, evento
  `PERSON_DETECTED` con confianza 0.84.
- Trazabilidad: `EVT-CAM-07-000001 -> INF-CAM-07-000001 -> producer
  yolo:person_detector -> model models/yolo11n.pt`.
- Latencia 1319 ms incluye la carga perezosa del modelo (primer inferencia);
  por frame posterior ~54.5 ms (LOOP-0018N).
- Sin credenciales ni frames almacenados; sin OpenCV en el evento.