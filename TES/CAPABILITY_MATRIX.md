# Matriz de Trazabilidad de Capacidades — TukeVision V3

**ID de Ejecución:** `TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08`
**Tipo de Integración:** `LIVE_RUN_ARTIFACT_OBSERVER` (Observador Pasivo Puro de Telemetría Real)
**Commit Base:** `59aa945`
**Estado Global:** `TV_F12_RUNTIME_TRUTH_CLOSED_WITH_EXTERNAL_LIMITATIONS`

| ID | Nombre de Capacidad | Estado Formal | Ruta de Implementación | Ruta de Pruebas | Evidencia Física (Run ID: `TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08`) | Dependencias | Última Decisión |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CAP-01** | Ingesta Multicámara (1..16 Canales) | `CERTIFIED` | `src/pipeline/`, `src/video/` | `tests/test_multicamera_view.py` | `evidence/TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08/physical_camera_health.json` | PyAV, OpenCV | DEC-008 |
| **CAP-02** | Focus HD con Perfil MAIN | `PHYSICALLY_VALIDATED` | `src/ui/tk_view.py` | `tests/test_focus_expansion.py` | `evidence/TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08/focus_hd_physical.json` | Tkinter, Pillow | DEC-003 |
| **CAP-03** | Inferencia Edge con OpenVINO | `CERTIFIED` | `src/pipeline/openvino_backend.py` | `tests/test_openvino_runtime.py` | `evidence/TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08/physical_camera_health.json` | openvino, numpy | DEC-001 |
| **CAP-04** | Rastreo Multi-Target (ByteTrack) | `CERTIFIED` | `src/tracking/` | `tests/test_person_tracker.py` | `evidence/TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08/liveness_physical.json` | ByteTrack | DEC-001 |
| **CAP-05** | Tokens de Diseño Unificados | `CERTIFIED` | `src/ui/design_tokens.py` | `tests/test_ux_productization.py` | `evidence/TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08/grid6_physical.json` | Tkinter | DEC-003 |
| **CAP-06** | Localización Completa (`es-CL`) | `CERTIFIED` | `src/localization/i18n.py` | `tests/test_ux_productization.py` | `evidence/TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08/grid6_physical.json` | Python standard | DEC-003 |
| **CAP-07** | Panel Técnico Colapsable (Video ≥ 80%) | `CERTIFIED` | `src/ui/tk_view.py` | `tests/test_ux_productization.py` | `evidence/TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08/grid6_physical.json` | Tkinter | DEC-003 |
| **CAP-08** | Paquetes de Evidencia & Hash SHA-256 | `CERTIFIED` | `src/evidence/models.py` | `tests/test_evidence_bundle.py` | `evidence/TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08/system_health_trace.json` | hashlib, PyAV | DEC-006 |
| **CAP-09** | Búsqueda Estructurada SQLite (`dvr://`) (P0-65) | `TESTED / OPERATIONAL` | `src/evidence/index.py` | `tests/test_index.py` | `evidence/TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08/zero_fake_runtime_gate.json` | sqlite3 | DEC-007 |
| **CAP-10** | Contrato de Firma ONVIF Media Signing | `CONTRACT_READY` | `src/evidence/models.py` | `tests/test_production_hardening.py` | N/A (Gated sin hardware) | cryptography | DEC-006 |
| **CAP-11** | Búsqueda Semántica / NLP Histórico (P0-65) | `TARGET / EVOLUTION` | `src/evidence/search_contract.py` | `tests/test_index.py` | N/A (En roadmap) | VLM / NLP | DEC-007 |
| **CAP-12** | Gobernanza de Políticas & Autonomía | `CERTIFIED` | `src/agent/actions/` | `tests/test_governed_actions.py` | `evidence/TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08/zero_fake_runtime_gate.json` | SQLite policy | DEC-004 |
| **CAP-13** | Supervisión Liveness & Anti-Falso Verde | `CERTIFIED` | `src/ui/tk_view.py` | `tests/test_live_sources.py` | `evidence/TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08/presentation_liveness.json` | Thread supervisor | DEC-008 |
