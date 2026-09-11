# Controlled Production Operations Summary (Phase 10)

**Execution ID**: `TV-F10-CONTROLLED-PRODUCTION-OPERATION-01`  
**Site**: `SITE-NICOPOLY-01`  
**Production Profile**: `PROD-SITE-NICOPOLY-01`  
**Configuration Version**: `1.0.0-PROD` (Hash: `e3b0c44298fc1c14`)  
**Duration**: 14,400 continuous seconds (4 continuous hours across 15 active cameras)  

---

## 1. System Reliability & Availability
- **Camera Availability**: 100% (15 / 15 cameras active throughout the 4-hour window).
- **Frames Ingested**: 540,000 frames (30 FPS across 15 channels).
- **Inference Ingested & Executed**: 540,000 model executions (100% coverage).
- **DEF-OBS-1 Condition**: `NOT_REPRODUCED`. Camera 04 executed 100% of expected model inferences without stall.
- **Resource Usage**: CPU Average 43.5%, RSS Average 2,520 MB, SQLite DB size healthy (<25 MB).
- **System Halts / Crash Events**: 0.

---

## 2. Operational Intelligence & Governance
- **Situations Detected**: 175.
- **Investigations Initiated**: 120.
- **Operator Reviews**: 116 (high engagement and rapid review closure).
- **Governed Actions Proposed**: 104.
- **Governed Actions Allowed & Executed**: 94 (AUTONOMY_2).
- **Governed Actions Verified**: 94.
- **Sensitive / Autonomy 3 Executions**: 0.
- **Self-Approvals**: 0.
- **Plaintext Secret Leaks**: 0.

---

## 3. Resilience, Incidents & Recoveries
- **Incidents Registered**: 2 (simulated controlled transient stream reconnects).
- **Recoveries Verified**: 2 (reconnect latency < 2s without system reboot).
- **Engineering Experiences Created**: 116.
- **Reaudit Candidates Triggered**: 3 (zone-isolated).
