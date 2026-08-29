# TukeVision — Operational Intelligence & Governed Video AI

TukeVision es una plataforma integral de inteligencia operacional local y gobernada que transforma video en tiempo real en observaciones estructuradas, estado espacial, investigación agentica, razonamiento en cascada, aprendizaje continuo y respuestas operacionales limitadas y auditables.

---

## Estado del Producto por Nivel de Madurez

### CERTIFIED & STABILIZED
- **Percepción y Detección en Tiempo Real**: Ingesta RTSP multicámara (hasta 15 cámaras concurrentes) con aceleración OpenVINO (CPU/GPU) y fallback verificado a PyTorch.
- **Seguimiento Temporal & Handoff Multicámara**: `TemporalEntityState`, homografía de planos de planta, viewshed y correlación espacial entre cámaras contiguas.
- **Orquestación de Atención & Agent Monitor**: Priorización determinista de situaciones que merecen atención (`AttentionOrchestrator`) y sesiones de investigación estructurada.
- **Cascade Intelligence**: Enrutamiento multinivel (`ReasoningRouter`): Determinista -> Local LLM (Qwen1.5-1.8B) -> Local VLM selectivo (Moondream2) con `AgentOutputValidator` (anti-alucinación, 0 hechos no soportados) y presupuesto adaptativo de CPU (`ReasoningBudget`).
- **Experience & Continuous Learning**: Almacenamiento local persistente (`ExperienceStore`), grafo de relaciones (`ExperienceGraph`), reauditoría selectiva (`SelectiveReauditEngine`) y detección de fallos conocidos (`FailureExperience`).
- **Acciones Operacionales Gobernadas**: Motor de políticas `ActionPolicyEngine` (default DENY, kill switches, safe mode), ejecución acotada `AUTONOMY_2` (alertas a operador, pinning de evidencia, tareas de revisión), aprobación humana obligatoria y anti-autoaprobación.
- **Pilot Readiness & Site Configuration**: Configuración canónica por sitio (`PilotSite`), protección estricta contra credenciales en texto plano (`SiteConfigurationValidator`), roles de operador (`VIEWER`, `OPERATOR`, `SUPERVISOR`, `ADMIN`), monitoreo de cobertura de inferencia (`InferenceCoverageGuard`) y reportes de sesión (`PilotReport`).

### PLANNED (Fuera de Alcance Fase 8)
- `AUTONOMY_3` (acciones físicas o sensibles externas: control de cerraduras, llamadas a emergencias, etc.).
- Reconocimiento facial y perfilamiento biométrico persistente.
- Auto-entrenamiento descontrolado o mutación autónoma de código/políticas.

---

## Requisitos del Sistema
- **SO**: Windows 10/11 (64-bit).
- **Python**: 3.12+ (entorno virtual `.venv`).
- **Inferencia**: Intel CPU / iGPU con OpenVINO runtime.

## Estructura del Código
- `src/core/`: Ingesta, supervisión de streams, OpenVINO runtime y fallback PyTorch.
- `src/spatial/`: Inteligencia espacial, homografías, zonas, viewshed y handoff.
- `src/agent/`: Agent Monitor, Attention Orchestrator, Cascade Intelligence, Experience Layer y Governed Actions.
- `src/pilot/`: Validación de sitios, guardias de cobertura, contratos de piloto y métricas.
- `evidence/`: Trazabilidad formal, benchmarks, manifests de soak test y veredictos certificados.

## Verificación y Tests
```powershell
.\.venv\Scripts\pytest.exe tests/ -v
```
