# RADAR RECONCILIATION
**MISSION:** TV-KNOWLEDGE-RADAR-RECONCILIATION-01
**DATE:** 2026-09-08

## 1. SOURCE INVENTORY

### ACTIVE (Adopted/Tested)
- OpenVINO Edge Runtime
- PyAV (FFmpeg C-bindings)
- ByteTrack
- Tkinter + DesignTokens
- SQLite Structured Indexing (P0-65)

### DORMANT (Evaluate/Watch/Target)
- ONVIF Media Signing (Profile T / G) - Pending hardware validation
- Attention Orchestrator Metrics (P0-66) - Telemetry active
- ONNX Runtime (Fallback)
- Semantic NLP (P0-65 target)
- DVR/NVR AI On-Demand
- WebRTC Gateway Auxiliar

### SUPERSEDED / REJECTED
- Detectron2 / Mask R-CNN (Rejected: Memory >4GB)
- Chromium/Electron UI (Rejected: High RAM, slow render)
- Grabación continua 24/7 en Host TukeVision (Rejected: DVR does this)

## 2. DORMANT KNOWLEDGE / MISSING KNOWLEDGE
The following seeds were recovered and reconciled:
- **ClearCam**: `ALREADY_IN_EXPERIENCE` (EXP-CLEARCAM-001..004)
- **Frigate**: `ALREADY_IN_RADAR` (CCTV lifecycle / multicamera resilience benchmark)
- **God's Eye View**: `ALREADY_DECIDED` (DEC-003)
- **Ambient.ai**: `ALREADY_DECIDED` (DEC-003)
- **HiFocus IntelliSeek**: `ALREADY_DECIDED` (DEC-007)
- **ONVIF Media Signing**: `ALREADY_DECIDED` (DEC-006, CAP-10)
- **YOLO people footfall**: `ALREADY_IN_RADAR` (SKILL.md)
- **claude-real-video**: `ALREADY_IN_RADAR` (SKILL.md)
- **SmolVLM**: `ALREADY_IN_RADAR` (HuggingFaceTB/SmolVLM2 family)
- **FastVLM**: `ALREADY_IN_RADAR` (apple/FastVLM-*)

## 3. NEW CANDIDATES (External Radar)

### JetBrains Junie
- **REPO_CANDIDATE_ID**: CAND-JUNIE
- **FORGE**: GITHUB
- **OWNER**: JetBrains
- **REPOSITORY**: junie
- **TYPE**: ENGINEERING_AGENT
- **ROLE**: DEVELOPMENT_TOOLING
- **DECISION**: BENCHMARK_COMPATIBILITY
- **DIRECT_CODE_REUSE**: NO
- **TUKEVISION MAPPING**: Agent tooling / CI-CD integration
- **REASON**: Evaluate agent capability paradigms.
- **REVISIT_WHEN**: Need for standardized CI/CD subagents.

### Avigilon / March Networks / SmartPSS
- **TYPE**: VMS / Hardware Interfaces
- **DECISION**: WATCH
- **REASON**: Enterprise VMS interoperability patterns.

### ONVIF Analytics Metadata
- **TYPE**: Protocol Extension
- **DECISION**: EVALUATE
- **TUKEVISION MAPPING**: `src/evidence/models.py`
- **REASON**: Standardize Edge AI inference output to physical NVRs.

### OC-SORT / CoTracker / TAPNet / Trace Anything
- **TYPE**: Tracking Models
- **DECISION**: BENCHMARK
- **TUKEVISION MAPPING**: `src/tracking/`
- **REASON**: ByteTrack is currently `ADOPTED`. Benchmark only if occlusion becomes a proven operational defect.

### Qwen3-VL
- **TYPE**: Vision Language Model (VLM)
- **DECISION**: WATCH
- **TUKEVISION MAPPING**: `src/evidence/search_contract.py`
- **REASON**: Alternative to SmolVLM for local edge deployments, depending on VRAM usage.

### NCSC agentic security patterns
- **TYPE**: Security Guidelines
- **DECISION**: EVALUATE
- **TUKEVISION MAPPING**: `src/agent/actions/`
- **REASON**: Reinforce Zero-Trust architecture in governed autonomy (DEC-004).

## 4. DECISIONS & REVISIT CONDITIONS
- Maintain **SQLite Structured Indexing** as operational truth for search, only advancing to NLP/VLM (SmolVLM/Qwen3-VL) when a clear operational need and hardware budget exist.
- Keep **ClearCam** experience patterns locked as the foundation for RTSP resilience (DEC-010).
- Do not incorporate new tracking algorithms (OC-SORT, CoTracker) without demonstrating failure of current `ByteTrack` pipeline.

---
## UPDATE_2026_09_08

### NEW_MATERIAL_FINDINGS
- **Agentic Video Understanding**: ADAPT_PATTERN / BENCHMARK_FUTURE. Added to P0-64/65/62/76. Vendor claims (up to 88% token reduction) logged as benchmark claims. Customer cloud upload prohibited.
- **Purpose-Bound AI Investigation**: ADOPT_GOVERNANCE_PATTERN. Added to P0-59/65/66/69. AI Search Result is now strictly a CANDIDATE_LEAD, not fact.
- **ONVIF Media Signing Framework**: BENCHMARK_READY. Upstream verified (onvif/media-signing-framework), MIT License.
- **screen2ipcam**: WATCH (SourceForge SF-SCREEN2IPCAM-001). Pattern for Universal Source Connector.
- **RapidVMS**: BENCHMARK_REFERENCE_ONLY. Direct integration rejected due to SECOND_NVR and ELECTRON_CONFLICT.

### NO_CHANGE_FINDINGS
- **GitLab**: Searched. No material finding. NO_CHANGE.
- **Profile M / Profile V**: No change. P1 / P2_WATCH_READINESS.
- **Radar / Thermal / Audio**: No change. RESERVE.
- **Hugging Face**: Maintained candidates (SmolVLM, etc.). No new promotion.

### SOURCE_VALIDATION
- onvif/media-signing-framework -> OFFICIAL_UPSTREAM, LICENSE: MIT
- screen2ipcam -> SourceForge, LICENSE/BINARY: Unverified/Watch

### TUKEVISION_MAPPING
- Agentic Video -> Adaptive Perception Budget, Cascade Intelligence, Semantic Investigation.
- Purpose-Bound Investigation -> Autonomy Governance, Privacy-Aware Evidence.
- screen2ipcam -> Universal Source Connector (P0-67).

### DECISION & REVISIT_WHEN
- Do not integrate external VLM clouds without explicit policy update.
- Revisit ONVIF hardware validation when signed hardware is physically available.
