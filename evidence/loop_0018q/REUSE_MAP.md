# LOOP-0018Q — Mapa de reuso (G4: REUSE BEFORE NEW DEVELOPMENT)

Fecha: 2026-08-16

## Resultado

Reuso en toda la capa de inferencia selectiva. NADA de E-02/E-03/E-04/E-05 se
reescribe; solo se consume lo ya certificado o ya adaptado en loops previos.

## Reuso directo (REUSE_AS_IS)

| Origen | Uso en LOOP-0018Q | Evidencia |
|---|---|---|
| `src/observations/activity.py::ObservationPolicy` | Decisión `should_analyze` por cámara en `SelectiveInferencePipeline.feed` | `src/inference/selective.py` importa `ObservationPolicy`; sin duplicación |
| `src/observations/activity.py::PROFILE_BALANCED` | Default seguro del pipeline | `src/inference/selective.py` |
| `src/observability/logging_setup.py::redact_rtsp_url` | Sanitización de refs/metadata en serialización | `contract.py`, `events.py`, `engines.py` |

## Reuso por composición (REUSE via COMPOSITION)

| Origen | Uso | Evidencia |
|---|---|---|
| `src/detection/person_detector.py::PersonDetector` | Backend real YOLO: `YoloInferenceEngine` delega `detector.detect(frame)` y traduce `DetectionResult -> InferenceResult` | `src/inference/engines.py` (carga perezosa, `close()` propaga) |

## Reuso de patrones ya adaptados en LOOP-0018P (REUSE_WITH_ADAPTATION previo)

| Patrón portable | Adaptado en | Consumido en LOOP-0018Q como |
|---|---|---|
| E-05 `quality_engine.py` (perfil + fallback seguro) | ObservationPolicy (LOOP-0018P) | Política QUALITY/BALANCED/ECONOMY reutilizada tal cual |
| E-02 `retail/trajectory.py` (retención acotada) | BoundedObservationQueue (LOOP-0018P) | `BoundedEventQueue` (mismo patrón de retención/overflow) |

## NO aplicable / NO migrado

- E-03 Identity/ReID: REQUIRES_DECISION (DEC-0013); NO se toca.
- E-04 Command Center UI: NOT_APPLICABLE (sin GUI en este loop).
- E-02 cuerpo completo (trayectorias/counting): NOT_APPLICABLE en este loop
  (retención acotada ya cubierta; cuerpo pendiente para correlación temporal,
  LOOP-0018R).

## Verificación de no-reescritura

- `src/capture/live_sources.py`: INTACTO (git-hash `6a9ae7e…`).
- `src/capture/source_manager.py`: NO reimplementado (git-hash `29e0274…`).
- `src/observations/activity.py`: NO reescrito (solo importado).
- `src/detection/person_detector.py`: NO modificado (solo compuesto).
- NEW_DEPENDENCIES = 0 (ultralytics/cv2/numpy ya presentes; solo stdlib nueva:
  threading/deque/dataclasses en `src/inference/`).