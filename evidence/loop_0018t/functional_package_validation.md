# FUNCTIONAL PACKAGE VALIDATION — LOOP-0018T

**Fecha:** 2026-08-16 · **Runtime:** BASE `.venv` (3.12.10) · **Paquete:** `dist\TukeVision`

## Componentes que el paquete contiene y puede inicializar

| Componente | Módulo | Inicializable desde el paquete |
|---|---|---|
| SourceManager | src/capture/source_manager.py | SÍ |
| ObservationPolicy | src/observations/activity.py | SÍ |
| ActivityLayer | src/observations/activity.py | SÍ |
| SelectiveInferencePipeline | src/inference/selective.py | SÍ |
| EventDetector | src/inference/events.py | SÍ |
| DeterministicInferenceEngine / build_engine | src/inference/engines.py | SÍ |
| LocalTracker | src/temporal/tracker.py | SÍ |
| build_tracker | src/temporal/tracker.py | SÍ |
| build_pipeline | src/inference/selective.py | SÍ |
| AdvanceChain (C1) | src/app/advance_chain.py | SÍ |
| Pipeline 2.1 | src/app/pipeline.py | SÍ |
| EvidenceStore / RiskCalculator / AlertEngine | src/evidence, src/risk, src/alerts | SÍ |

## Verificación ejecutada

```
ALL_2_2_COMPONENTS_INITIALIZABLE
FUNCTIONAL_PACKAGE_OK
```

Los 12 componentes se construyen con `config/default.json` del propio paquete.
La cadena 2.2 se compone vía `AdvanceChain.build(cfg, source_manager)` (C1) y la
cadena 2.1 vía `Pipeline(config=cfg)` — ambas certificadas en regresión 370/370.

## Observación

El FutureWarning de `supervision` (target=None) aparece al importar; es un
deprecation conocido de la dependencia, sin impacto funcional ni bloqueo.

— Fin de functional_package_validation.md (LOOP-0018T)