# LOOP-0018P — MAPA SOURCE -> TARGET DE COMPONENTES REUTILIZADOS

Trazabilidad origen -> adaptación -> destino de lo migrado/reutilizado en
LOOP-0018P. No se copió ningún árbol completo: solo comportamiento útil y
verificable.

| Origen | Adaptación | Destino (BASE) | Estado |
|---|---|---|---|
| E-05 `QualityProfile` (QUALITY/ECONOMY/AUTO, portable) | Perfiles de análisis con fallback seguro; AUTO descartado; añadido BALANCED | `src/observations/activity.py` `ObservationPolicy` (QUALITY/BALANCED/ECONOMY, `max_analysis_fps`, `sampling_interval_frames`, clamp sanitizador) | REUSE_WITH_ADAPTATION |
| E-05 fallback "sin datos -> default seguro" | Si fps <= 0 -> fps=15 fallback; config inválida -> default BALANCED | `ObservationPolicy.sampling_interval_frames` + `ObservationPolicy.__init__` | REUSE_WITH_ADAPTATION |
| SourceManager `BOUNDED_QUEUE` (BASE, certificado LOOP-0018N) | Cola FIFO acotada por cámara con overflow explícito drop-oldest/drop-newest | `src/observations/activity.py` `BoundedObservationQueue` | REUSE_WITH_ADAPTATION |
| `redact_rtsp_url` (BASE, LOOP-0001) | Redacción de credenciales en serialización y metadatos | `ActivityObservation.to_dict()` + `ActivityLayer._default_producer` | REUSE_AS_IS |
| `SourceManager.list_sources`/`health` (BASE) | Registro por composición del inventario público y fps real | `ActivityLayer.register_from_source_manager` | ALREADY_EXISTS_IN_BASE (composición) |
| `config/default.json` (BASE) | Bloque `observation` con perfiles QUALITY/BALANCED/ECONOMY (default BALANCED) | `config/default.json` `observation` | ALREADY_EXISTS_IN_BASE (extendido) |
| Convención timestamps UTC ISO (BASE) | `_utc_now_iso` con sufijo Z | `ActivityObservation.timestamp` + `clock` inyectable | REUSE_WITH_ADAPTATION |

## Componentes NUEVOS (no reutilizados de nada, creados en LOOP-0018P)

| Componente | Responsabilidad |
|---|---|
| `src/observations/activity.py` (nuevo) | Activity/Observation Layer mínima completa: `ActivityObservation`, `BoundedObservationQueue`, `ObservationPolicy`, `ActivityLayer`. |
| `tests/test_activity_layer.py` (nuevo) | 39 tests deterministas de la capa. |
| `evidence/loop_0018p/` (nuevo) | Evidencia del loop. |

## Descarte explícito (y por qué)

| Componente descartado | Por qué |
|---|---|
| E-02 `TrajectoryStore`/`FlowCounter` | Pertenece a INFERENCE posterior (tracking retail); no es observación canónica. |
| E-04 `tk_view.py`/`state.py` | GUI fuera de alcance del contrato mínimo; sin visualización necesaria para certificar con tests sintéticos. |
| E-03 `identity/**` | REQUIRES_EXTERNAL_EXTENSION/REQUIRES_DECISION (DEC-0013 + `_PROJECT_ROOT` hardcodeado); queda fuera. |
| E-05 stream subtype decision (`get_stream_type`) | Dominio CAPTURE; no modificar SourceManager. |
| E-05 datos de auditoría hardcodeados | Reemplazables por capacidades dinámicas (resource_budget.md); no se migran datos estáticos. |