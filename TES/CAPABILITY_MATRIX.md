# Matriz de Trazabilidad de Capacidades — TukeVision

| ID | Nombre de Capacidad | Estado Formal | Ruta de Implementación | Ruta de Pruebas | Evidencia Física (Run ID: `TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04`) | Dependencias | Última Decisión | Commit Actualizado |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CAP-01** | Ingesta Multicámara (1..16 Canales) | `CERTIFIED` | `src/pipeline/`, `src/video/` | `tests/test_multicamera_view.py` | `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/physical_camera_health.json` | PyAV, OpenCV | DEC-008 | `b0b992a` |
| **CAP-02** | Focus HD con Perfil MAIN | `CERTIFIED` | `src/ui/tk_view.py` | `tests/test_focus_expansion.py` | `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/focus_hd_physical.json` | Tkinter, Pillow | DEC-003 | `b0b992a` |
| **CAP-03** | Inferencia Edge con OpenVINO | `CERTIFIED` | `src/pipeline/openvino_backend.py` | `tests/test_openvino_runtime.py` | `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/physical_camera_health.json` | openvino, numpy | DEC-001 | `b0b992a` |
| **CAP-04** | Rastreo Multi-Target (ByteTrack) | `CERTIFIED` | `src/tracking/` | `tests/test_person_tracker.py` | `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/liveness_physical.json` | ByteTrack | DEC-001 | `b0b992a` |
| **CAP-05** | Tokens de Diseño Unificados | `CERTIFIED` | `src/ui/design_tokens.py` | `tests/test_ux_productization.py` | `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/ux_physical_acceptance.json` | Tkinter | DEC-003 | `b0b992a` |
| **CAP-06** | Localización Completa (`es-CL`) | `CERTIFIED` | `src/localization/i18n.py` | `tests/test_ux_productization.py` | `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/ux_physical_acceptance.json` | Python standard | DEC-003 | `b0b992a` |
| **CAP-07** | Panel Técnico Colapsable (Video ≥ 80%) | `CERTIFIED` | `src/ui/tk_view.py` | `tests/test_ux_productization.py` | `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/grid6_physical.json` | Tkinter | DEC-003 | `b0b992a` |
| **CAP-08** | Paquetes de Evidencia & Hash SHA-256 | `CERTIFIED` | `src/evidence/models.py` | `tests/test_evidence_bundle.py` | `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/system_health_trace.json` | hashlib, PyAV | DEC-006 | `b0b992a` |
| **CAP-09** | Búsqueda Estructurada SQLite (`dvr://`) | `TESTED` | `src/evidence/index.py` | `tests/test_index.py` | `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/zero_fake_runtime_gate.json` | sqlite3 | DEC-007 | `b0b992a` |
| **CAP-10** | Contrato de Firma ONVIF Media Signing | `CONTRACT_READY` | `src/evidence/models.py` | `tests/test_production_hardening.py` | N/A (Gated sin hardware) | cryptography | DEC-006 | `b0b992a` |
| **CAP-11** | Búsqueda Semántica / NLP Histórico | `TARGET` | `src/evidence/search_contract.py` | `tests/test_index.py` | N/A (En roadmap) | VLM / NLP | DEC-007 | `b0b992a` |
| **CAP-12** | Gobernanza de Políticas & Autonomía | `CERTIFIED` | `src/agent/actions/` | `tests/test_governed_actions.py` | `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/zero_fake_runtime_gate.json` | SQLite policy | DEC-004 | `b0b992a` |
| **CAP-13** | Supervisión Liveness & Anti-Falso Verde | `CERTIFIED` | `src/ui/tk_view.py` | `tests/test_live_sources.py` | `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/liveness_physical.json` | Thread supervisor | DEC-008 | `b0b992a` |
