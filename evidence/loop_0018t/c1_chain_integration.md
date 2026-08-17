# C1 — INTEGRACIÓN DE CADENA 2.2 -> 2.1 (LOOP-0018T)

**LOOP:** 0018T · **Fase:** 1 (C1) · **Fecha:** 2026-08-16
**BASE_CODE:** `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision`
**Branch:** `product/loop-0018r-temporal-tracking` · **HEAD (pre):** `cfad93163b9fe1b992e87026b0adbb437c518cee`

---

## 1. Análisis del punto de conexión (definición exacta de la evidencia)

Fuente: `evidence/loop_0018s/current_product_certification.md` (§2.1, §2.2) y
`evidence/loop_0018s/gate_matrix.md` (G20, condición C1).

### 2.1 Cadena operativa del PRODUCTO (la única cableada de punta a punta)

```
SOURCE (VideoSource FILE | WebcamSource | RTSPSource E01)
   -> PersonDetector (YOLO11n)                     src/detection/person_detector.py
   -> PersonTracker (ByteTrack)                    src/tracking/person_tracker.py
   -> Zone (polígono)                              src/context/zone.py
   -> ObservationEngine (PERSON_*_ZONE)            src/observations/engine.py
   -> EventEngine (PERMANENCIA_PROLONGADA)         src/events/engine.py
   -> RuleEngine (RULE-PERMANENCIA-001)            src/business/rules.py
   -> RiskCalculator (0-100)                       src/risk/calculator.py
   -> AlertEngine (umbral 60)                      src/alerts/engine.py
   -> EvidenceStore (frame.jpg + metadata.json)    src/evidence/store.py
   -> [on_frame] FrameSnapshot -> UiController -> TkApp
   -> VideoWriter -> data/output/processed.mp4
```

### 2.2 Capas del PRODUCT ADVANCE (implementadas + certificadas sintéticamente, NO cableadas)

```
RTSP CAMERAS -> SourceManager (hilo+cola+health por cámara)   src/capture/source_manager.py
                     │  (composición: register_from_source_manager — existente, SIN llamador)
                     ▼
        ActivityLayer -> ObservationPolicy -> BoundedObservationQueue   src/observations/activity.py
                     ▼
        SelectiveInferencePipeline (POLICY->INFERENCE->EVENT)          src/inference/selective.py
                     ▼
        LocalTracker (EVENT -> LOCAL_TRACK -> TEMPORAL_ACTIVITY)       src/temporal/tracker.py
```

## 2. Campos del análisis C1

| Campo | Valor |
|---|---|
| **SOURCE_CAPABILITY** | Actividad (observaciones), inferencia selectiva (eventos) y tracking temporal (tracks/actividades) disponibles como contratos certificados (0018p 39/39, 0018q 42/42, 0018r 33/33). |
| **TARGET_CAPABILITY** | Producto real = cadena 2.1 unicámara; la cadena 2.2 NO está conectada a ningún entry point. |
| **CURRENT_CONNECTION** | Ninguna en runtime: `register_from_source_manager` existe en ActivityLayer y SelectiveInferencePipeline pero sin llamador; LocalTracker solo expone `register_camera`. Único puente 2.1<->2.2: `SourceManager._default_rtsp_source -> RTSPSource`. |
| **EXPECTED_CONNECTION** | Un adapter de composición que registre las cámaras del SourceManager en Activity + Selective + LocalTracker y encole cada frame a través de toda la cadena (observación -> evento -> track), usando solo contratos existentes. |
| **MISSING_CONNECTION** | Faltaba: (a) un llamador en runtime de `register_from_source_manager`; (b) la composición manual de LocalTracker por cámara; (c) el cableado observación->inferencia->track. |
| **FILES_REQUIRED** | `src/app/advance_chain.py` (nuevo adapter), `tests/test_advance_chain.py` (nuevos tests). |
| **TESTS_REQUIRED** | 11 tests deterministas de wiring (build config-driven, registro, feed completo, aislamiento, summary sin secretos, close idempotente). |

## 3. Solución aplicada (adapter/wiring mínimo, contratos existentes)

`src/app/advance_chain.py` — clase `AdvanceChain`:

- `AdvanceChain.build(config, source_manager)`: fábrica config-driven que construye
  `ActivityLayer(config)`, `SelectiveInferencePipeline` (vía `build_pipeline(config["inference"])`)
  y `LocalTracker` (vía `build_tracker(config["temporal"])`) usando los builders
  certificados; fail-safe explícito con `AdvanceChainError`.
- `register_from_source_manager()`: da llamador en runtime a
  `ActivityLayer.register_from_source_manager(sm)` y
  `SelectiveInferencePipeline.register_from_source_manager(sm)`, y compone
  `LocalTracker.register_camera(camera_id)` por cámara (contrato por cámara).
- `feed(camera_id, frame_index, fps, frame, metadata)`: recorre la cadena
  `activity.feed -> observation_ref -> selective.feed -> event -> tracker.ingest(event) -> track`.
  Devuelve dict JSON-serializable (obs/event/track, cualquiera puede ser None por política).
- `summary()`: estado auditable agregado, sin secretos ni frames.
- `close()`: shutdown en orden inverso (tracker -> selective -> activity), idempotente.

Ninguna capa existente fue reescrita ni reimplementada. `live_sources.py` (E-01),
`source_manager.py`, `observations/activity.py`, `inference/*`, `temporal/*` quedan
INTACTOS (hashes verificados en precheck).

## 4. Verificación

### 4.1 Tests enfocados (nuevos)

```
Ran 11 tests in 0.030s  OK   (tests/test_advance_chain.py)
```

Casos: build config-driven; config inválida -> AdvanceChainError; sin bloque
`inference` -> error; feed tras close -> error; registro en las 3 capas; feed
recorre toda la cadena (obs -> OBJECT_DETECTED -> track); política saltea frame 1
(sin obs/event/track); frame negro -> observación sin evento; aislamiento de
fallo de backend por cámara; summary sin `password`/`secret`; close limpio e
idempotente.

### 4.2 Regresión completa

```
Ran 370 tests (359 baseline + 11 nuevos) in 24.4s  OK
```

NEW_REGRESSIONS = 0.

### 4.3 COMPILEALL

```
COMPILEALL_OK  (python -m compileall -q src scripts tests)
```

## 5. Alcance y límites (respeto a la política anti-avance del loop)

- C1 cierra el gap H1 de LOOP-0018S en el nivel de **wiring**: la cadena 2.2 ya
  tiene un adapter de composición invocable desde runtime usando los contratos
  certificados.
- NO se integró la cadena 2.2 como reemplazo de la 2.1 en el pipeline GUI
  (pipeline.py/controller.py/run_interface.py permanecen intactos); eso es el
  avance P1 completo (16-32h) fuera del alcance de LOOP-0018T.
- NO se añadió persistencia de `evidence_ref` en disco (H3): el adapter usa los
  refs en memoria de las capas; materialización en disco es P1.
- NO se añadieron dependencias nuevas; no se reimplementó ninguna capa.

## 6. Verificación de hashes (capas tocadas por composición)

| Archivo | SHA-256 | Estado |
|---|---|---|
| src/observations/activity.py | 114b6a3715024d7f142f6b7082950f6fffc4e41b | INTACTO |
| src/inference/selective.py | 855f20bd421289b442d66941365d7dec5ba09241 | INTACTO |
| src/inference/engines.py | (sin cambios; build_pipeline delega) | INTACTO |
| src/temporal/tracker.py | ca51c4b9a7974f1b27e358691b8e572c14185c1d | INTACTO |
| src/capture/source_manager.py | 29e0274beac2f623fcd24feca7f9c9bf1c85f33e | INTACTO |
| src/capture/live_sources.py (E-01) | 6a9ae7e1187c2b8644b3f9f73abbcb5d689b61a7 | INTACTO |

Nuevos archivos (NO reimplementación):
- `src/app/advance_chain.py` (adapter/wiring)
- `tests/test_advance_chain.py` (tests deterministas)

## 7. Conclusión C1

> **C1 = CLOSED** (wiring de cadena 2.2 -> 2.1 realizado como adapter de
> composición mínimo con contratos existentes; llamador en runtime para
> `register_from_source_manager`; 11/11 tests enfocados; 370/370 regresión;
> 0 regresiones nuevas; ninguna capa certificada reescrita).
> NOTA: la integración funcional completa (2.2 reemplazando/ampliando la 2.1 en
> el pipeline GUI + materialización de evidencia en disco) es P1, fuera del
> alcance de LOOP-0018T (política anti-avance).

— Fin de c1_chain_integration.md (LOOP-0018T)