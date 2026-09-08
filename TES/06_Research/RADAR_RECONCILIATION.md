# RADAR RECONCILIATION
**MISSION:** TV-KNOWLEDGE-RADAR-RECONCILIATION-02
**DATE:** 2026-09-08
**MODE:** ACTIVE / TES-FIRST / ANTI-DORMANCY

## 1. SOURCE INVENTORY

### ACTIVE BASELINE (Adopted/Tested)
- OpenVINO Edge Runtime
- PyAV (FFmpeg C-bindings)
- ByteTrack
- Tkinter + DesignTokens
- SQLite Structured Indexing (P0-65)

### ACTIVE EVALUATION QUEUE
Todos los elementos anteriormente clasificados como `DORMANT`, `EVALUATE`, `WATCH`, `TARGET` o `BENCHMARK` pasan a una cola activa de reevaluación condicionada por brechas reales y revisión periódica.

- ONVIF Media Signing
- ONVIF Analytics Metadata / Profile M
- ONVIF Profile V readiness
- Attention Orchestrator Metrics (P0-66)
- ONNX Runtime fallback
- Semantic NLP / Semantic Investigation
- DVR/NVR AI On-Demand
- WebRTC Gateway Auxiliar
- ClearCam
- Frigate
- God's Eye View
- Ambient.ai / agentic monitoring
- HiFocus IntelliSeek
- Agentic Video Understanding
- Purpose-Bound Investigation
- March Networks
- Avigilon
- SmartPSS Lite
- screen2ipcam
- RapidVMS (reference only)
- OC-SORT
- CoTracker
- TAPNet
- Trace Anything
- SmolVLM
- FastVLM
- Qwen3-VL
- NCSC agentic security patterns
- JetBrains Junie
- Access Control / PACS patterns
- Radar / Thermal / Audio (reserved but radar-visible)

### REJECTED / RESTRICTED
Estos elementos permanecen visibles y pueden reabrirse sólo por `REVISIT_WHEN` explícito:
- Detectron2 / Mask R-CNN as primary edge runtime
- Chromium/Electron UI
- Grabación continua 24/7 en Host TukeVision
- ClearCam direct code integration / product replacement
- RapidVMS direct product integration

## 2. TES-FIRST PROBLEM-SOLVING CONTRACT

Ante un problema técnico o operacional:

```text
PROBLEM
→ EXPERIENCE_STORE SEARCH
→ TECHNOLOGY_RADAR SEARCH
→ DECISION_LOG SEARCH
→ RADAR_RECONCILIATION SEARCH
→ MATCH CANDIDATES
→ MINIMUM DECISIVE BENCHMARK
→ ADAPT / INTEGRATE / ALREADY_RESOLVED / RESERVE / REJECT
→ REGRESSION TEST
→ TES UPDATE
```

No crear un módulo, dependencia o arquitectura nueva sin registrar primero:

`TES_CONSULTED=YES`

## 3. DORMANT KNOWLEDGE RECOVERY

### ClearCam
- **STATUS:** ACTIVE_ENGINEERING_CANDIDATE
- **DECISION:** ADAPT_BENCHMARK
- **DIRECT_CODE_REUSE:** NO (GPL-3.0 boundary)
- **ACTIVE TARGETS:** RTSP resilience, playback freshness, selective inference, stationary/recovery tracking, event/semantic search.
- **REVISIT_WHEN:** cualquier defecto o mejora potencial en SourceManager, frame freshness, tracking, compute budget o investigation.

### Frigate
- **STATUS:** ACTIVE_BENCHMARK_REFERENCE
- **TARGETS:** ffmpeg/go2rtc lifecycle, camera recovery, multicamera resilience, hardware acceleration, events/search.
- **REVISIT_WHEN:** fallos de ingestión, lifecycle, recovery o necesidad de comparación NVR OSS madura.

### God's Eye View
- **STATUS:** ADAPTED / PERIODIC_REVIEW
- **TARGETS:** spatial state, viewshed, freshness, provenance, map/agent context.

### Ambient.ai
- **STATUS:** ADAPT_PATTERN / PERIODIC_REVIEW
- **TARGETS:** selective attention, case management, operator-load metrics.

### HiFocus IntelliSeek
- **STATUS:** ADAPT_PATTERN / ACTIVE_WHEN_INVESTIGATION
- **TARGETS:** local on-demand historical analysis without full-video embeddings.

### ONVIF Media Signing
- **STATUS:** CONTRACT_READY / ACTIVE_HARDWARE_WATCH
- **TARGETS:** origin signing, provenance, evidence verification.

### Agentic Video Understanding
- **STATUS:** ACTIVE_BENCHMARK_CANDIDATE
- **TARGETS:** goal-directed temporal search, dynamic re-sampling, selective high-FPS inspection.

### Purpose-Bound Investigation
- **STATUS:** ADOPT_GOVERNANCE_PATTERN
- **TARGETS:** purpose/case/scope/permission/audit; AI result = candidate lead.

### Tracking candidates
- **OC-SORT:** ACTIVE_BENCHMARK when ByteTrack shows ID-switch/stationary/occlusion weakness.
- **CoTracker / TAPNet / Trace Anything:** ACTIVE_EVALUATION only for point/dense/recovery needs.

### Local VLM candidates
- **SmolVLM / FastVLM / Qwen3-VL:** ACTIVE_BENCHMARK when selective contextual analysis is required; never continuous by default.

### Enterprise VMS experience
- **March Networks / Avigilon / SmartPSS Lite:** ACTIVE_REFERENCE for multisitio, access/video, investigation, UX and interoperability patterns.

### NCSC
- **STATUS:** ACTIVE_GOVERNANCE_REFERENCE
- **REVISIT_WHEN:** agent permissions, tools, autonomy or safe-mode capability changes.

### Access Control / PACS
- **STATUS:** CONTRACT_READYNESS_ACTIVE
- **TARGET:** neutral `AccessObservation` and correlation with video/location/time.
- **RULE:** no Mercury/Alocity proprietary module.

## 4. REEVALUATION RULES

### Triggered reevaluation
Reevaluate immediately when:
- a defect matches a stored experience;
- a new source materially changes maturity/performance/license;
- a previously reserved capability becomes a real product requirement;
- a baseline component can gain measurable stability, efficiency, accuracy or operator value.

### Periodic reevaluation
The daily TukeVision Radar must compare new findings not only against the Plan Maestro but against this active queue and the Experience Store.

### Minimum decisive benchmark
Do not build a long project when a small experiment can decide. Prefer:
- same input;
- same hardware;
- same acceptance metric;
- baseline vs candidate;
- explicit cost/risk/license result.

## 5. NO LONGER VALID

The following behavior is prohibited:

```text
DISCOVER
→ DOCUMENT IN TES
→ NEVER REVISIT
```

Required behavior:

```text
DISCOVER
→ VERIFY
→ MAP
→ ACTIVE EVALUATION
→ DECIDE
→ LEARN
```

## 6. KNOWLEDGE FRESHNESS

Every Radar cycle must:
1. inspect material external developments;
2. inspect all active TES candidates affected by those developments;
3. compare them with current TukeVision problems and roadmap;
4. update the recommended state (`ADAPT`, `INTEGRATE`, `BENCHMARK`, `RESERVE`, `REJECT`, `ALREADY_RESOLVED`);
5. identify stale assumptions or obsolete rejection reasons;
6. preserve source/licence/provenance.

Knowledge freshness is part of engineering readiness, not optional documentation hygiene.
