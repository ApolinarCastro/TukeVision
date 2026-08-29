# HANDOFF TO CODEX — MACRO-OC-01 → MACRO-OC-01-R

**EXECUTION_ID:** MACRO-OC-01-R (FULL INTEGRATION REPAIR & COMPLETION)
**Fecha:** 2026-08-19
**Baseline Autoritativo:** `61d7ab38516d9da656a53c71d919f9857eda50d4`
**HEAD Actual:** working tree (cambios MACRO-OC-01 + MACRO-OC-01-R sin commitear)

---

## Resumen de MACRO-OC-01-R

OpenCode (Integration Engine) ha reparado y completado la integración construida
en MACRO-OC-01: corrigió imports rotos (SCENE/OPERATOR), completó el ciclo de
políticas de aprendizaje con gate de inferioridad, arregló el mapeo enum/string
del catálogo multitienda, cableó host/user/password en el runtime local, añadió
routing de evidencia por tienda (sin contaminación cross-store), corrigió
GRID_6 y el preset switching del Command Center, declaró PTZ como
CAPABILITY_GATED/NOT_CERTIFIED y añadió 63 tests verticales dedicados.
Sin micro-loops, sin reconstrucción de core protegido.

---

## Flags de Salida — MACRO-OC-01-R

| Flag | Estado | Evidencia |
|------|--------|-----------|
| SCENE_IMPORT | ✅ | `import src.scene` OK (exports corregidos) |
| SCENE_VERTICAL | ✅ | `tests/test_scene_engine.py` (Observation→Track→Activity→Event→Sequence→Timeline) |
| OPERATOR_IMPORT | ✅ | `import src.operator` OK |
| OPERATOR_VERTICAL | ✅ | `tests/test_operator_insight.py` (traza store/cameras/tracks/events/evidence) |
| LEARNING_CURRENT_POLICY | ✅ | `CurrentPolicy` dataclass + dict round-trip + `validation_metrics`/`effective_since_utc` |
| LEARNING_CANDIDATE_CREATION | ✅ | `PolicyManager.create_candidate` (base verificada; versión inexistente → error) |
| LEARNING_VALIDATION | ✅ | `CandidatePolicy.validate` determinista (precision/recall/f1/fpr) + `validate_candidate` |
| INFERIOR_CANDIDATE_GATE | ✅ | `promote_candidate` → `INFERIOR_CANDIDATE -> MUST_NOT_REPLACE_CURRENT` (`PolicyRejectionError`) |
| MULTISTORE_CATALOG | ✅ | `StoreCatalog` 2 tiendas, enums `RecorderType`/`ZoneRole`, `summary()` sin secretos |
| MULTISTORE_RUNTIME_WIRING | ✅ | `MulticameraRuntime` usa host/user/password locales + validación de consistencia de host |
| STORE_LIFECYCLE | ✅ | `store_ids()`, `active_stores()`, `store_status()` |
| EVIDENCE_NAMESPACE | ✅ | `evidence_root_for()` / `camera_evidence_namespace()` / `evidence_routing()` |
| NO_CROSS_STORE_CONTAMINATION | ✅ | `tests/test_multistore_runtime_wiring.py::TestEvidenceNamespace` |
| GRID16/9/6/4/1 | ✅ | `tests/test_command_center_layouts.py::TestGridLayouts` |
| PRESET_SWITCHING | ✅ | `cycle_grid_preset()` + `tk_view._on_cycle_grid` cambia set renderizado y geometría |
| FOCUS_NAVIGATION | ✅ | Back-to-grid / Prev / Next sobre catálogo completo |
| DIGITAL_ZOOM | ✅ | `build_zoomed_display_image` (presentacional, sin upscale) |
| PTZ_STATUS | ✅ | `ptz_status()` → `CAPABILITY_GATED` / `certified=False` / `ptz_command()` siempre False |
| QW03_PRESERVED | ✅ | `src/observability/system_health.py` intacto; `test_system_health` OK |
| SCENE_TESTS | ✅ | 12 tests |
| OPERATOR_TESTS | ✅ | 8 tests |
| LEARNING_TESTS | ✅ | 9 tests |
| DEPLOYMENT_TESTS | ✅ | 7 tests |
| MULTISTORE_TESTS | ✅ | 11 tests (catalog + runtime wiring + evidence namespace) |
| COMMAND_CENTER_TESTS | ✅ | 16 tests |
| FULL_REGRESSION | ✅ | 555 passed, 4 skipped (492 baseline + 63 nuevos) |
| DIFF_CHECK | ✅ | Core protegido sin reescritura; solo adaptación de imports en scene/operator |
| NEW_REGRESSIONS | ✅ | 0 (555 passed tras cleanup) |

**PROTECTED_CORE_REWRITTEN:** NO
**SECOND_PIPELINE_CREATED:** NO
**SECOND_EVIDENCE_STORE_CREATED:** NO

---

## Resumen de Ejecución

OpenCode (Integration Engine) ha completado la construcción de las verticales de TukeVision reutilizando el núcleo certificado (LOOP-0018Y, LOOP-0019A-R2), sin micro-loops, sin reconstrucción de core, y sin sustitución de componentes certificados sin gap demostrado.

---

## Flags de Salida (SALIDA)

| Flag | Estado | Evidencia |
|------|--------|-----------|
| FOUR_CAMERA_LIMIT_REMOVED | ✅ | `grid_layout.py` + `MultiCameraViewModel` config-driven 1→4→16→N |
| MULTISTORE_DOMAIN_IMPLEMENTED | ✅ | `src/domain/models.py` + `catalog.py` (Organization→Store→Recorder→Camera) |
| DVR_NVR_SOURCES_SUPPORTED | ✅ | `RecorderConfig` con `recorder_type` enum + `channel_number` + `stream_main`/`stream_sub` |
| DIRECT_IP_SOURCES_SUPPORTED | ✅ | `StoreConfig.direct_cameras` + `CameraConfig.credentials_ref` |
| DYNAMIC_CONFIG | ✅ | `StoreCatalog.from_dict()` soporta bloque `multistore` + legacy fallback |
| 16_CAMERA_ARCHITECTURE | ✅ | `GRID_PRESETS = (1,4,6,9,16)` + `grid_cells()` para GRID_6 (1 main + 5 aux) |
| COMMAND_CENTER_GRID | ✅ | `tk_view.py` grid dinámico con `grid_cells()` + rowspan/colspan |
| FOCUS_NAVIGATION | ✅ | Click/doble-clic/back-to-grid/prev/next/fullscreen en `tk_view.py` |
| DIGITAL_ZOOM | ✅ | `build_zoomed_display_image()` + rueda ratón en focus mode |
| PTZ_SUPPORT | ✅ | UI gateada por `ptz_capability.supported` + `Controller.ptz_command()` stub |
| HEALTH_INTEGRATION | ✅ | `SystemHealthSnapshot.store_health` + `CentralQueryService` agregación |
| SCENE_MODEL | ✅ | `src/scene/models.py` (SceneObservation→SceneTrack→SceneActivity→SceneEvent) |
| ZONE_MODEL | ✅ | `ZoneConfig` + `ZoneAdapter` (rect/polygon) + `InteractionIntelligence` |
| INTERACTION_MODEL | ✅ | `InteractionEvent` (person-zone, person-POI, person-person) |
| TEMPORAL_SCENE_MODEL | ✅ | `SceneSequence` + `EvidenceTimeline` + `CrossCameraCorrelation` |
| OPERATOR_INSIGHT_FOUNDATION | ✅ | `OperatorInsightGenerator` + `OperatorQueryEngine` (AG-05 contract) |
| CASE_MEMORY_FOUNDATION | ✅ | `CaseMemory` (RAW/REVIEWED/TRAINING_ELIGIBLE) |
| LEARNING_DATASET_FOUNDATION | ✅ | `FeedbackDataset` versionado + `FeedbackDatasetBuilder` |
| CENTRAL_EDGE_FOUNDATION | ✅ | `DeploymentTopology` + `EdgeCentralSplit` + `CentralQueryService` |

**PROTECTED_CORE_REWRITTEN:** NO
**SECOND_PIPELINE_CREATED:** NO

---

## Archivos Cambiados / Creados

### Dominio Multistore (OC-01, OC-02, OC-03)
- `src/domain/models.py` — Entidades Organization/Store/Recorder/Camera + `PTZConfig` + `CameraHealthState`
- `src/domain/catalog.py` — `StoreCatalog` config-driven → `CameraDescriptor` (SECRET_LEAK=0)
- `config/multistore.example.json` — Config de ejemplo 2 tiendas, 2 DVR, 1 IP directa, PTZ, zonas

### Command Center (OC-04, OC-05, OC-06, OC-07)
- `src/ui/grid_layout.py` — `grid_cells()` con `GridCell` (rowspan/colspan para GRID_6)
- `src/ui/tk_view.py` — Grid dinámico, store selector, zona filter, PTZ controls, digital zoom, focus navigation
- `src/ui/controller.py` — `stores()`, `store_cameras()`, `store_zones()`, `select_store()`, `ptz_capability()`, `ptz_command()`
- `docs/OC-04_ARCHIVE_CLASSIFICATION.md` — Clasificación portable (REUSE/ADAPT/KEEP_CURRENT/REJECT)

### QW-03 Health Integration (OC-03)
- `src/observability/system_health.py` — `StoreHealthSnapshot` + `SystemHealthSnapshot.store_health` + `CentralQueryService`
- `scripts/run_multicamera.py` — Pasa `catalog` a `SystemHealthSampler`

### Scene Intelligence (OC-08..OC-12)
- `src/scene/models.py` — SceneObservation, SceneTrack, SceneActivity, SceneEvent, SceneSequence, EvidenceTimeline, ZoneConfig, InteractionEvent, OperatorInsight
- `src/scene/engine.py` — `SceneEngine`, `ZoneAdapter`, `InteractionIntelligence` (componen sobre core certificado)

### Expert Operator AI (OC-13, OC-14)
- `src/operator/engine.py` — `OperatorInsightGenerator` (explicable, ACTIVITY_REQUIRES_REVIEW), `OperatorQueryEngine` (structured queries)

### Learning Foundation (OC-15..OC-17)
- `src/learning/memory.py` — `CaseMemory` (RAW/REVIEWED/TRAINING_ELIGIBLE), `FeedbackDataset` versionado, `CurrentPolicy`/`CandidatePolicy`/`PolicyManager`

### Deployment (OC-18)
- `src/deployment/topology.py` — `EdgeCentralSplit`, `DeploymentTopology`, `CentralQueryService`, `EdgeCaptureService`

### Reparaciones MACRO-OC-01-R
- `src/scene/__init__.py` — exports corregidos (sin imports rotos desde `scene.models`); `import src.scene` OK
- `src/scene/models.py` — `track_id` como `str`, `store_id`, classmethods `from_activity_observation`/`from_local_track`/`from_temporal_activity`, `OperatorInsight` con traza completa
- `src/scene/engine.py` — `CrossCameraCorrelator` (corrección de import), composición sobre contratos certificados (bbox/class_name eliminados del flujo scene)
- `src/operator/engine.py` — `store_id` en `OperatorQuery`, index por store/camera/track/event
- `src/learning/memory.py` — `@dataclass` en `CurrentPolicy`/`CandidatePolicy`, `validate()` real, gate `INFERIOR_CANDIDATE -> MUST_NOT_REPLACE_CURRENT`
- `src/domain/catalog.py` — enums `RecorderType`/`ZoneRole`, `summary()` con detalle por cámara sin secretos, `store_ids()/active_stores()/store_status()`, `credential_resolver`, `evidence_root_for()/camera_evidence_namespace()/evidence_routing()`
- `src/ui/grid_layout.py` — `grid_layout` GRID_6 sin duplicar/omitir cámaras, `cycle_grid_preset()` (presets 1/4/6/9/16)
- `src/ui/tk_view.py` — `_on_cycle_grid` cambia set renderizado + geometría; `_update_side_panel_cameras` robusto; PTZ gateado por `ptz_status().certified`
- `src/ui/controller.py` — `ptz_status()` (CAPABILITY_GATED / NOT_CERTIFIED), `ptz_command()` nunca envía sin implementación física
- `src/deployment/topology.py` — fix `defaultdict` sin importar (Block 11)
- `scripts/run_multicamera.py` — `MulticameraRuntime` cablea host/user/password locales, valida consistencia de host, deriva `evidence_root` por tienda

---

## Tests

- **555 passed, 4 skipped** (venv Python 3.12) — 492 baseline + 63 tests verticales nuevos (MACRO-OC-01-R)
- Tests verticales dedicados (Block 9): `test_scene_engine.py`, `test_operator_insight.py`,
  `test_learning_memory.py`, `test_deployment_topology.py`, `test_multistore_catalog.py`,
  `test_multistore_runtime_wiring.py`, `test_command_center_layouts.py`
- Tests existentes preservados (G1-G10 certificados LOOP-0019A-R2)
- Tests stale transformados a API config-driven (MACRO-OC-01)
  - `test_multicamera_view.py` — `MultiCameraViewModel(camera_ids=...)`
  - `test_multicamera_entrypoint.py` — test recorder cameras descriptor subtype
  - `test_loop_0019b_r2.py` — `_view()` helper para camera_ids
  - `test_tk_multicamera_renderer.py` — verifica ausencia de hardcoded CAM-001..004

---

## Arquitectura Map

```
┌─────────────────────────────────────────────────────────────────┐
│                        CENTRAL (AG-07)                          │
│  CentralQueryService ── Health/Events/Review/Search agregados  │
│  PolicyManager ── CurrentPolicy / CandidatePolicy promotion    │
│  CaseMemory + FeedbackDatasetBuilder ── Learning loop          │
└──────────────────────────▲──────────────────────────────────────┘
                           │ upstream_data (metadata only)
┌──────────────────────────▼──────────────────────────────────────┐
│                        STORE EDGE (xN)                          │
│  EdgeCaptureService ── SourceManager + OperationalPipeline     │
│  SceneEngine ── SceneEvent → SceneSequence → EvidenceTimeline  │
│  OperatorInsightGenerator ── ACTIVITY_REQUIRES_REVIEW          │
│  SystemHealthSampler ── StoreHealthSnapshot → Central          │
│  UiController + TkApp ── Grid 1/4/6/9/16 + Focus + PTZ + Zoom  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Riesgos Conocidos

| Riesgo | Mitigación |
|--------|------------|
| PTZ físico no implementado (ONVIF/SDK pendiente) | `PTZ_STATUS = CAPABILITY_GATED / NOT_CERTIFIED`; UI nunca habilita controles sin implementación física certificada |
| Supervision no integrado | `ZoneAdapter` usa ray-casting nativo; Supervision opcional (SDL-03) |
| Cross-camera correlation limitado a topología | DEC-0040: sin ReID biométrico; solo correlación temporal/topológica |
| Learning dataset no entrena automáticamente | Policy promotion manual requerido (SDL-07, SDL-09, SDL-20) |
| Full-res streaming evitado | Solo sub-streams + metadata + evidence_refs upstream |

---

## Entrypoints Operador

| Entrypoint | Comando | Descripción |
|------------|---------|-------------|
| Command Center Multicámara | `python scripts/run_multicamera.py` | UI Tk con grid config-driven, store selector, PTZ, health |
| Health Check | `python scripts/health_check.py` | Verificación host + cámaras |
| Behavior Review | `review_behavior_signals.bat` | Consola revisión humana QW-00 |

---

## Compatibilidad

- **Baseline certificado:** `61d7ab38516d9da656a53c71d919f9857eda50d4`
- **Core protegido intacto:** SourceManager, LocalTracker, ActivityLayer, EvidenceStore, Pipeline, BehaviorEngine (LOOP-0018Y validated)
- **Legacy fallback:** `config/default.json` (business + correlation) mapea a `STORE-001` con 4 cámaras VIDEO_FILE
- **SECRET_LEAK=0:** Credenciales solo via `credentials_ref` → env vars; nunca en config/git/logs

---

## Ítems No Implementados (Aprobados, Pendientes Loop Futuro)

| Ítem | Spec | Condición GO |
|------|------|--------------|
| Pose/Action Intelligence | AG-04 §2.4 | `REEVALUATE_IF_BBOX_TEMPORAL_INSUFFICIENT` (FROZEN) |
| Supervision PolygonZone/LineZone | AG-04 §2.2 | Gap geométrico demostrado en Nicopoly |
| Apprise Notifications | SDL-04 | Requiere integración operator console |
| MediaPipe Pose / OpenVINO | SDL-10, SDL-15 | `EVIDENCE_CONTEXT_GAP` resuelto por QW-04 clips |
| Entrenamiento automático | AG-06 | Requiere `OPERATOR_VALIDATION` explícito |

---

## Estado Final

**STATUS:** `STOPPED_FOR_CODEX`

**READY_FOR_CERTIFICATION:** YES
**HANDOFF_TO_CODEX:** COMPLETE (MACRO-OC-01 + MACRO-OC-01-R)

---

*Generado por OpenCode (Integration Engine) bajo gobernanza ANTIGRAVITY*