# LOOP-0018Q — Resultados de tests

Fecha: 2026-08-16
Intérprete: `C:\Users\ASUS Zenbook\Documents\TukeVision-portable\.venv\Scripts\python.exe`
(Python 3.12.10; ultralytics 8.4.115; cv2 5.0.0; BASE `.venv` roto)

## Tests focalizados — deterministas

Comando: `python -m unittest tests.test_inference_layer -v`

Resultado: **42/42 OK** (0.010 s)

Cobertura (TestInferenceResultContract, TestPolicyProfilesSelective, TestEventDetection,
TestBoundedEventQueue, TestConfigFailsafeAndDeterminism):

- Contrato/serialización `InferenceResult` (roundtrip, JSON, immutabilidad, validación
  bbox/confianza/latencia, metadata acotada, sin objetos OpenCV).
- Perfiles QUALITY/BALANCED/ECONOMY: processed/skipped correctos;
  ECONOMY < BALANCED < QUALITY en consumo; override por cámara.
- Independencia por 4 cámaras (CAM-01/03/05/07).
- Threshold config-driven (strict 0.5 -> sin evento; lax 0.1 -> evento).
- `InferenceResult -> Event` (OBJECT_DETECTED/PERSON_DETECTED; regla específica con
  `class_name` gana en empate; clase car -> OBJECT_DETECTED).
- event_id, timestamp UTC, inference_ref, evidence_ref.
- Cola bounded: drop_oldest/drop_newest, descartados, maxlen, pipeline bounded.
- Aislamiento de fallos del backend (engine que lanza -> inference_errors, otras
  cámaras intactas).
- Config inválida -> fail-safe (perfil inválido -> BALANCED; regla inválida ignorada;
  build_pipeline: backend/events/cola inválidos -> error explícito).
- Secret leak: metadata y observation_ref con canary redactados en serialización.
- Determinismo: mismas entradas -> mismas salidas (métricas + eventos).
- Shutdown/close: engine cerrado, feed posterior -> SelectiveInferenceError.

## Tests focalizados — backend real YOLO (separados)

Comando: `python -m unittest tests.test_inference_real_backend -v`

Resultado: **4/4 OK** (3.557 s). Modelo `models/yolo11n.pt` + `data/temp/zidane.jpg`.

- `test_real_inference_produces_result`: >= 1 detección real, timestamp UTC Z,
  engine_name `yolo`, latency >= 0.
- `test_real_inference_result_serializable`: `to_dict()` JSON-serializable.
- `test_real_result_to_event`: resultado real -> PERSON_DETECTED/OBJECT_DETECTED.
- `test_real_selective_pipeline_synthetic_frames`: pipeline BALANCED con 4 cámaras
  y frames sintéticos sobre el motor YOLO real: invariantes de métricas cumplidas.

Nota: si el modelo o la imagen faltan, el caso se marca SKIP (no es fallo de
arquitectura); en este entorno ambos existen y se ejecutaron.

## Regresión completa

Comando: `python -m unittest discover -s tests -p "test_*.py"`

Resultado: **326/326 OK** (24.7 s)

- Baseline previo: 280/280.
- Nuevos: 46 (42 deterministas + 4 reales).
- Regresiones: 0.

## Compilación

`python -m compileall -q src tests` -> EXIT=0 (`COMPILEALL_OK`). `__pycache__` ignorado
por git (sin ruido en el repo).