# LOOP-0018Q — Política de observación (config-driven) y configuración de inferencia

Fecha: 2026-08-16

## Bloques de `config/default.json`

### `observation` (heredado de LOOP-0018P, NO modificado)

```json
"observation": {
  "default_profile": "BALANCED",
  "profiles": {
    "QUALITY":  { "max_analysis_fps": 4.0 },
    "BALANCED": { "max_analysis_fps": 2.0 },
    "ECONOMY":  { "max_analysis_fps": 1.0 }
  }
}
```

### `inference` (NUEVO en LOOP-0018Q, +14 líneas)

```json
"inference": {
  "backend": "yolo",
  "model": "models/yolo11n.pt",
  "class_ids": [0],
  "confidence_threshold": 0.35,
  "device": "cpu",
  "image_size": 640,
  "event_queue_maxlen": 16,
  "event_queue_overflow": "drop_oldest",
  "events": [
    { "type": "OBJECT_DETECTED", "min_confidence": 0.35 },
    { "type": "PERSON_DETECTED", "min_confidence": 0.35, "class_name": "person" }
  ]
}
```

## Fail-safe

- `build_engine`: backend ausente/inválido -> `InferenceConfigError` explícito
  (nunca silencio peligroso en runtime).
- `build_pipeline`: `inference.events` no-lista / sin reglas válidas /
  `event_queue_maxlen < 1` / `event_queue_overflow` inválido -> `SelectiveInferenceError`.
- `ObservationPolicy` (LOOP-0018P): perfil inválido -> fallback BALANCED + warning.
- `EventDetector._normalize_rule`: regla inválida se ignora con warning; config
  inválida -> estado conocido (sin eventos), no error silencioso peligroso.

## Default seguro (G11)

- BALANCED ~2fps por cámara. NO inferencia continua 15fps x 4.
- Backend default `yolo` en CPU; modelo yolo11n.pt; class_ids [0] (personas).
- Threshold 0.35 para detección YOLO y umbral mínimo de evento.