# TukeVision — Estado Operacional y Técnico Actual (Phase 9)

**Execution ID**: `TV-F9-CONTROLLED-REAL-PILOT-ACTIVATION-01`  
**Baseline F8 Certified Commit**: `fc5b1662d9dfae11760328345cfcd3f205895345`  
**Baseline F8 Certified Tag**: `v3-phase8-operational-pilot-ready-20260829`  
**Branch**: `phase9/controlled-real-pilot-activation`  
**Certification Status**: `REAL_PILOT_ACTIVE_STABLE`

---

## Capacidades Certificadas Integradas

1. **Activación de Piloto Real Controlado (`PilotSession`)**:
   - Ingesta y validación estricta de inputs del cliente (`ClientOperationalInputRecord`) con hashing criptográfico inmutable.
   - Paquete de activación de sitio (`RealSiteActivationPackage`) versión `1.0.0-PROD`.
   - Verificación previa obligatoria mediante Dry-Run (`REAL_SITE_DRY_RUN = PASS`).
2. **Percepción & Edge Ingestion**:
   - Ingesta RTSP de 15 cámaras concurrentes con OpenVINO y fallback verificado.
   - Supervisión activa de cobertura con `InferenceCoverageGuard` (DEF-OBS-1 condición `NOT_REPRODUCED`).
3. **Inteligencia Espacial & Handoff**:
   - Mapeo de zonas, homografía de planta y viewshed.
   - Continuidad de entidades temporales entre cámaras contiguas.
4. **Atención & Agent Monitor**:
   - Orquestación determinista de atención.
   - Sesiones de investigación estructuradas (`InvestigationSession`).
5. **Cascade Intelligence**:
   - Razonamiento multinivel: Determinista -> Qwen1.5-1.8B -> Moondream2.
   - Validación estricta anti-alucinación (`AgentOutputValidator`).
6. **Experience & Continuous Learning**:
   - Memoria operacional local (`ExperienceStore`, SQLite).
   - Grafo de relaciones de experiencia (`ExperienceGraph`).
   - Detección de recurrencia de fallos (`FailureExperience`).
7. **Acciones Gobernadas (Governed Actions)**:
   - Motor de políticas con default DENY (`ActionPolicyEngine`).
   - Autonomía 2 limitada para acciones internas reversibles.
   - Autonomía 3 deshabilitada (`AUTONOMY_3_ENABLED=false`).
   - Gobernanza de roles y anti-autoaprobación.
