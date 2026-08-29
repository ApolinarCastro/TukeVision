# TukeVision — Estado Operacional y Técnico Actual (Phase 8)

**Execution ID**: `TV-F8-OPERATIONAL-PILOT-READINESS-IMPLEMENT-01`  
**Baseline F7 Certified Commit**: `58b013fe2383c79414d76daeb335d8c180eba915`  
**Baseline F7 Certified Tag**: `v3-phase7-governed-actions-stable-20260829`  
**Branch**: `phase8/operational-pilot-readiness`  
**Certification Status**: `OPERATIONAL_PILOT_READY`

---

## Capacidades Certificadas Integradas

1. **Percepción & Edge Ingestion**:
   - Ingesta RTSP de 15 cámaras concurrentes con OpenVINO y fallback verificado.
   - Supervisión activa de cobertura con `InferenceCoverageGuard`.
2. **Inteligencia Espacial & Handoff**:
   - Mapeo de polígonos de zona, homografía de planta y viewshed.
   - Continuidad de entidades temporales entre cámaras contiguas.
3. **Atención & Agent Monitor**:
   - Orquestación determinista de atención sin sobrecarga de razonamiento.
   - Creación de sesiones estructuradas de investigación (`InvestigationSession`).
4. **Cascade Intelligence**:
   - Razonamiento multinivel: Determinista -> Qwen1.5-1.8B -> Moondream2.
   - Validación estricta anti-alucinación (`AgentOutputValidator`).
5. **Experience & Continuous Learning**:
   - Memoria operacional local (`ExperienceStore`, SQLite).
   - Grafo de relaciones de experiencia (`ExperienceGraph`).
   - Detección de recurrencia de fallos (`FailureExperience`).
6. **Acciones Gobernadas (Governed Actions)**:
   - Motor de políticas con default DENY (`ActionPolicyEngine`).
   - Autonomía 2 limitada para acciones internas reversibles.
   - Autonomía 3 deshabilitada (`AUTONOMY_3_ENABLED=false`).
   - Trazabilidad y no-autoaprobación.
7. **Preparación para Piloto Operacional (Pilot Readiness)**:
   - Configuración portable por sitio (`PilotSite`).
   - Validación estricta de credenciales (`SiteConfigurationValidator`).
   - Roles de operador (`VIEWER`, `OPERATOR`, `SUPERVISOR`, `ADMIN`).
   - Reconciliación canónica P0 y separación técnica de inputs de cliente (UC-001).
