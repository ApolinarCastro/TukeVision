# LOOP-0018P — INVENTARIO DE APLICABILIDAD E-02 / E-04 / E-05 (REUSE BEFORE NEW DEVELOPMENT)

## Criterio

Clasificación de cada componente candidato del portable (LABORATORY) y del BASE
según REUSE BEFORE NEW DEVELOPMENT:
`ALREADY_EXISTS_IN_BASE`, `REUSE_AS_IS`, `REUSE_WITH_ADAPTATION`,
`NOT_APPLICABLE`, `BLOCKED_EXTERNAL_DEPENDENCY`.

Regla del loop: migrar solo comportamiento útil y verificable, con trazabilidad
origen -> adaptación -> destino. NO copiar árboles por semejanza.

## E-02 — Retail trajectory (`src/retail/trajectory.py`, portable)

| Componente | Clasificación | Justificación |
|---|---|---|
| `TrajectoryStore.update/get_trajectory/clear` | NOT_APPLICABLE | Seguimiento de trayectorias retail (track_id -> puntos). Pertenece a la capa INFERENCE posterior, no a OBSERVATION/POLICY mínima. No se migra. |
| `FlowCounter` (entradas/salidas) | NOT_APPLICABLE | Métricas de flujo retail; no es observación canónica por cámara. |
| `TrajectoryStore` retención acotada (max_points/max_tracks) | REUSE_WITH_ADAPTATION (concepto) | El patrón de retención acotada con política explícita informa a `BoundedObservationQueue` (drop-oldest/drop-newest). NO se copia el archivo; solo el concepto de cola acotada, ya consolidado en el BASE con BOUNDED_QUEUE del SourceManager. |
| `TrackTrajectory.add_point` bounded | NOT_APPLICABLE | Depende de track_id/personas; fuera de alcance. |

## E-04 — Command Center UI (`src/ui/tk_view.py`, `src/ui/state.py`, portable)

| Componente | Clasificación | Justificación |
|---|---|---|
| `tk_view.py` (grid, fullscreen, selector de canal) | NOT_APPLICABLE | La directiva no construye GUI nueva salvo pieza mínima reutilizable necesaria. El contrato mínimo OBSERVATION/POLICY se certifica con tests sintéticos deterministas; no requiere visualización. La recertificación visual queda para un loop posterior. |
| `src/ui/state.py` (estado de UI) | NOT_APPLICABLE | Acoplado a Tk y al controller; no aporta al contrato mínimo. |

## E-05 — Quality engine (`src/capture/quality_engine.py`, portable)

| Componente | Clasificación | Justificación |
|---|---|---|
| `QualityProfile` (QUALITY / ECONOMY / AUTO) | REUSE_WITH_ADAPTATION | Se reutiliza el CONCEPTO de perfil de análisis con fallback seguro. Se adapta a `ObservationPolicy` con QUALITY/BALANCED/ECONOMY (AUTO no aplica al contrato de sampling determinista). |
| `get_stream_type` / `get_subtype` (subtype 0/1) | NOT_APPLICABLE | Decisión de stream RTSP (subtype), dominio CAPTURE/SourceManager. La política de LOOP-0018P decide sampling/análisis por cámara SIN modificar SourceManager. |
| `CameraStreamCapability` + datos hardcodeados de auditoría | NOT_APPLICABLE | Datos de auditoría estáticos (LOOP-0017); reemplazables por capacidades medidas dinámicamente (resource_budget.md). El sampling usa fps real de `SourceManager.health()`. |
| Fallback seguro "sin datos -> default seguro" | REUSE_WITH_ADAPTATION | Mismo principio: sin fps conocido -> fallback seguro (intervalo con fps=15). Aplicado en `ObservationPolicy.sampling_interval_frames`. |

## Componentes del BASE revisados

| Componente | Clasificación | Justificación |
|---|---|---|
| `src/capture/source_manager.py` | ALREADY_EXISTS_IN_BASE (composición) | Se consume por composición vía `ActivityLayer.register_from_source_manager` (list_sources + health). NO se reescribe. |
| `src/observations/models.py` (Observation zone/retail) | ALREADY_EXISTS_IN_BASE | Modelo retail existente; NO se modifica (241 regresión intacta). El nuevo `ActivityObservation` es complementario y desacoplado de zonas/tracks. |
| `src/events/models.py`, `src/evidence/models.py` | ALREADY_EXISTS_IN_BASE | Capas EVENT/EVIDENCE posteriores; no se adelantan. `evidence_ref` queda como referencia opcional de contrato. |
| `src/observability/logging_setup.py` (`redact_rtsp_url`) | REUSE_AS_IS | Usado por `ActivityObservation.to_dict()` y `ActivityLayer` (defensa en profundidad contra credenciales). |
| `config/default.json` | ALREADY_EXISTS_IN_BASE | Se extiende con el bloque `observation` (config-driven seguro). |
| `BOUNDED_QUEUE` (SourceManager) | REUSE_WITH_ADAPTATION (concepto) | Convención de cola acotada certificada; adaptada a observaciones en `BoundedObservationQueue`. |

## BLOCKED_EXTERNAL_DEPENDENCY

Ninguno. Todas las decisiones se resuelven con stdlib + dependencias ya presentes (NEW_DEPENDENCIES=0).