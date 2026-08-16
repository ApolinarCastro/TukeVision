# LOOP-0018Q — Arquitectura y contrato mínimos

Fecha: 2026-08-16

## Flujo

```
CAMERA/SOURCE -> OBSERVATION -> POLICY -> SELECTIVE INFERENCE
                                            -> EVENT -> EVIDENCE_REFERENCE
```

- `SourceManager` (LOOP-0018N) entrega frames por cámara lógica.
- `ObservationPolicy` (LOOP-0018P, REUTILIZADA) decide `should_analyze(camera, frame_index, fps)`
  según perfil QUALITY/BALANCED/ECONOMY (config-driven, default BALANCED ~2fps).
- `SelectiveInferencePipeline.feed` consulta la política ANTES de invocar el motor:
  solo los frames autorizados consumen presupuesto del backend (frame budgeting real).
- `InferenceEngine.infer` devuelve `InferenceResult` (inmutable, serializable, sin
  credenciales, sin objetos OpenCV, metadata acotada <= 4096 B, timestamp UTC Z).
- `EventDetector.detect(result)` produce `InferenceEvent` si una regla config-driven
  se cumple (threshold por tipo; regla específica con `class_name` gana en empate).
- El evento entra en `BoundedEventQueue` por cámara (overflow drop_oldest/drop_newest,
  contador de descartados). Evidencia por referencia (`evidence_ref`), sin frames.

## Módulos (`src/inference/`)

| Módulo | Responsabilidad |
|---|---|
| `contract.py` | `InferenceDetection`, `InferenceResult` (frozen, `to_dict`/`from_dict`), `InferenceEngine` ABC, errores (`InferenceError`, `InferenceConfigError`, `InferenceValidationError`) |
| `engines.py` | `DeterministicInferenceEngine` (sintético determinista, reloj inyectable, latencia simulada) · `YoloInferenceEngine` (compone PersonDetector, carga perezosa, traducción de errores) · `build_engine(config)` |
| `events.py` | `InferenceEvent` (canónico, `to_dict`/`from_dict`), `EventDetector` (config-driven), `BoundedEventQueue` |
| `selective.py` | `SelectiveInferencePipeline` (policy + motor + detector + cola + métricas + aislamiento + close), `build_pipeline(config)` |

## Contrato `InferenceResult`

Campos: `inference_id`, `camera_id`, `timestamp` (UTC Z), `engine_name`, `model_name`,
`producer`, `detections` (tuple `InferenceDetection`), `latency_ms`, `confidence`,
`observation_ref`, `evidence_ref`, `metadata` (acotada). `frozen=True` (inmutable).

`InferenceDetection`: `class_id`, `class_name`, `confidence`, `x1/y1/x2/y2`; valida
confianza en [0,1] y bbox consistente.

## Contrato `InferenceEvent`

Campos: `event_id`, `camera_id`, `timestamp` (UTC Z), `event_type`
(OBJECT_DETECTED/PERSON_DETECTED), `confidence`, `producer`, `model`,
`observation_ref`, `inference_ref`, `evidence_ref` (opcional), `metadata` (acotada).
Trazable: `inference_ref` apunta al `InferenceResult`; `observation_ref` al origen.

## Métricas por cámara y total

`considered`, `processed`, `skipped_by_policy`, `inference_errors`,
`events_generated`, `latency_ms_sum`, `latency_ms_last`, `latency_ms_avg`,
`queued_events`, `event_queue_dropped` (por cámara) + `profile`. Memoria acotada
(contadores + colas bounded), sin crecimiento ilimitado.

## Invariantes

- SELECTIVE_INFERENCE = YES (decisión real por política, no declarativa).
- BACKEND_FAILURE_ISOLATION = YES (fallo de CAM-X -> `inference_errors`, no detiene
  las demás; sin bucles de retry infinitos: cada feed decide una vez).
- NO_FRAME_STORAGE = YES (el frame nunca se serializa).
- CONFIG_DRIVEN_THRESHOLDS = YES (threshold/reglas desde config, nunca hardcode).
- SECRET_LEAK = 0 (`redact_rtsp_url` en refs y toda cadena serializada).
- NO_CONTINUOUS_15FPS_X4 = YES (default BALANCED ~2fps).
- NEW_DEPENDENCIES = 0.
- E-01/SourceManager/ObservationLayer intactos.