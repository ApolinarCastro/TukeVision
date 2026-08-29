# CURRENT_PRODUCT_CERTIFICATION — LOOP-0018S

**LOOP:** 0018S · **Modo:** CERTIFY_CURRENT_PRODUCT (SOLO LECTURA; sin implementación) · **Fecha:** 2026-08-16
**BASE_CODE:** `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision`
**Branch:** `product/loop-0018r-temporal-tracking` · **HEAD:** `cfad93163b9fe1b992e87026b0adbb437c518cee` (loop-0018r, 16-08 18:55)
**Working tree:** limpio en trackeados; 2 untracked esperados (`evidence/loop_0018m_r1/`, `src/capture/live_sources.BASE_preE01.bak.py`) documentados en `evidence/loop_0018r/HASHES.md`.
**Regla de evidencia:** conversaciones/planes NO son evidencia. Solo código (archivo:línea), tests y evidencia escrita en `evidence/`. Credenciales redactadas (REDACTED). Canario de trazado RTSP: no presente en este documento.
**Fuente primaria:** worker_90 (ronda 1), verificado por revisor S4 (review.md).

---

## 1. Verificación de compilación y baseline

- `py_compile` sobre `src/capture/source_manager.py`, `src/inference/*`, `src/temporal/*`, `src/observations/activity.py`, `src/app/pipeline.py` → **EXIT=0**.
- Regresión completa: **359/359 PASS** (unittest, runner documentado; ver `test_certification.txt`).
- COMPILEALL: PASS (exit 0). SECRET_LEAK: 0.

## 2. Cadena arquitectónica REAL (solo lo que existe en código hoy)

### 2.1 Cadena operativa del PRODUCTO (heredada, la ÚNICA cableada de punta a punta)

```
SOURCE (VideoSource FILE | WebcamSource | RTSPSource E01)
   -> PersonDetector (YOLO11n)                       src/detection/person_detector.py
   -> PersonTracker (ByteTrack)                      src/tracking/person_tracker.py
   -> Zone (polígono, ENTERED/REMAINED/EXITED)       src/context/zone.py
   -> ObservationEngine (PERSON_*_ZONE)              src/observations/engine.py
   -> EventEngine (PERMANENCIA_PROLONGADA)           src/events/engine.py
   -> RuleEngine (RULE-PERMANENCIA-001)              src/business/rules.py
   -> RiskCalculator (score 0-100)                   src/risk/calculator.py
   -> AlertEngine (umbral 60)                        src/alerts/engine.py
   -> EvidenceStore (data/evidence/<alert_id>/frame.jpg+metadata.json)  src/evidence/store.py
   -> [on_frame] FrameSnapshot -> UiController -> TkApp   src/ui/*
   -> VideoWriter -> data/output/processed.mp4 (recording monofuente)
Estado live: RTSPSource {OPEN, STALLED, RECONNECTING, FAILED} -> final_status=STREAM_LOST
```

### 2.2 Capas del PRODUCT ADVANCE (implementadas, certificadas sintéticamente, **NO cableadas** a 2.1)

```
RTSP CAMERAS -> SourceManager (hilo+cola+health por cámara, aislamiento)   src/capture/source_manager.py
                     │  (composición: register_from_source_manager — existe en API, sin llamador en runtime)
                     ▼
        ActivityLayer -> ObservationPolicy(QUALITY/BALANCED/ECONOMY) -> BoundedObservationQueue
                     │  src/observations/activity.py
                     ▼
        SelectiveInferencePipeline (POLICY->INFERENCE->EVENT) -> BoundedEventQueue
                     │  src/inference/selective.py (+ engines: Deterministic | Yolo; events: EventDetector)
                     ▼
        LocalTracker (EVENT -> LOCAL_TRACK -> TEMPORAL_ACTIVITY -> OPERATIONAL_EVIDENCE refs)
                     src/temporal/tracker.py (duck-typing de InferenceEvent)
```

**Punto crítico (H1):** ningún entry point de producto (`src/app/pipeline.py`, `src/ui/controller.py`, `scripts/*.py`) importa `src.inference`, `src.temporal` ni `src.observations.activity` (verificado por grep independiente del revisor S4). El encadenamiento 2.2 solo existe como código compilable + tests/demos (0018p: 39/39; 0018q: 42/42 + demo real; 0018r: 33/33). El único puente implementado entre 2.1 y 2.2 es `SourceManager._default_rtsp_source` → `RTSPSource` (composición sobre E01, `src/capture/source_manager.py`), usado físicamente en loop_0018o.

## 3. Hallazgos y riesgos

| # | Severidad | Hallazgo | Detalle |
|---|---|---|---|
| H1 | CRÍTICO | Product Advance sin integración | Las 4 capas nuevas (ActivityLayer/ObservationPolicy, SelectiveInference, LocalTracker, puente SourceManager) están implementadas y certificadas sintéticamente, pero **no están conectadas al pipeline que ejecuta el producto**. El producto real sigue siendo la cadena 2.1 monofuente. Leer `evidence/loop_0018q|r` y asumir "el producto hace inferencia selectiva y tracking temporal" es falso. |
| H2 | MEDIO | dist OUTDATED | Cualquier despliegue desde `dist/` entrega código del 11-08 (pre-E01, pre-advance). MANIFEST (git_head `4e530f3`) es la fuente de verdad; regenerar antes de cualquier entrega. |
| H3 | MEDIO | Flujo de evidencia real solo en el loop viejo | La única evidencia persistida en runtime es `frame.jpg`+metadata.json de alertas de permanencia (EvidenceStore). `evidence_ref` del nuevo pipeline (InferenceEvent/LocalTrack first/latest/best) no se materializa en disco: son referencias en memoria/tests. |
| H4 | BAJO | Estado del repo | La task asumía cambios sin commitear; en realidad todo está en HEAD `cfad931`. Solo 2 untracked esperados. `.venv` del BASE tiene el shebang roto (ruta inexistente de otro usuario); los loops usan el `.venv` portable como intérprete (laboratorio). |
| H5 | BAJO | Capacidades con estado dual | zones/dwell/risk/alerts/evidence son CERTIFIED dentro del flujo viejo, pero NO existen para el flujo multicámara nuevo (per-camera pipeline PARTIAL). El salto "4 cámaras capturadas" → "4 cámaras analizadas" sigue sin cerrarse. |
| H6 | BAJO | Scaffolding vacío | `src/incidents/`, `src/shared/`, `src/visualization/` son directorios vacíos en BASE y dist; no declarar como capacidades. |
| H7 | INFO | Sin regresiones | Regresión completa documentada 359/359; modelos y assets presentes (`models/yolo11n.pt`, `data/input/Video.mp4`). |

## 4. Estado ejecutable preliminar (dist/)

- Existe: `dist/TukeVision/` + `dist/TukeVision-portable.zip` (5,1 MB), build 2026-08-15 19:32.
- MANIFEST: `package_version 0.1.0`, `build_date 2026-08-15`, **`git_head 4e530f3` (2026-08-11)**, `spec_certified_base cf876a9`.
- **NO contiene:** `src/inference/`, `src/temporal/`, `src/capture/source_manager.py`, `src/observations/activity.py`, tests/; `live_sources.py` del build = versión PRE-E01 (13.214 B, 11-08).
- **Clasificación: OUTDATED** (no CERTIFIED, no NOT_FOUND). Detalle en `official_executable_status.md`.

## 5. Veredicto

> El producto REAL actual está certificado como: **núcleo unicámara SPEC-0001 + E-01 COMPAT cableado de punta a punta (CERTIFIED), multicámara 4 física CERTIFIED (captura), capas PRODUCT ADVANCE implementadas y certificadas sintéticamente pero NO cableadas (H1), ejecutable OUTDATED (H2), evidencia del avance solo en memoria (H3).** No hay regresiones; 359/359 PASS; compileall PASS; SECRET_LEAK=0.

— Fin de current_product_certification.md (LOOP-0018S)
