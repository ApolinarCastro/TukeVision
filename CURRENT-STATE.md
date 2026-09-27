# TukeVision — Current Execution State

**UPDATED:** 2026-09-27  
**PROJECT:** TukeVision  
**CANONICAL_REMOTE_BRANCH:** `feature/product-evolution-v1`  
**CANONICAL_REMOTE_HEAD_AT_UPDATE:** `d8c3e8afe44cdb6e97cf345fd8d56d3c4801451b`  
**EXECUTION_PROTOCOL:** `07_PROJECT_EXECUTION_OS_TASKVIEW_ECC` + `06_ANTI_HALLUCINATION_AND_RESOURCE_GATE`  
**PROTOCOL_STATUS:** `ACTIVE`

---

## 1. Fuente de verdad y alcance

El contexto de chat NO es fuente de verdad del proyecto.

Antes de cualquier análisis, diseño, cambio de arquitectura, código, depuración, prueba, recomendación o continuación material se debe recuperar el estado persistente disponible:

- `README.md`
- este `CURRENT-STATE.md`
- tarea/bloqueador actual
- `TES/DECISION_LOG.md`
- fallos/riesgos/bloqueadores persistidos
- aceptación/evidencia disponible
- baseline o Golden Dataset cuando aplique
- `TES/ACTIVE_EVALUATION_PROTOCOL.md`
- ECC vigente cuando el trabajo involucre agentes, memoria, skills, workflows, planificación, verificación, seguridad, contexto, aprendizaje continuo o harness

Ciclo obligatorio:

```text
persistent state
→ evidence
→ smallest next action
→ plan
→ test
→ implement
→ review
→ verify
→ remember
→ improve
→ persist
```

---

## 2. Estado remoto verificable

La comparación del baseline de runtime `0d3640571dfcd737958903ae3fb52b8fe425cee4` contra el HEAD canónico indicado arriba muestra que los commits posteriores en la rama remota son cambios bajo `TES/`.

Por tanto, para este control point:

```text
REMOTE_RUNTIME_BASELINE = 0d3640571dfcd737958903ae3fb52b8fe425cee4
REMOTE_TES_AHEAD = YES
REMOTE_RUNTIME_PRODUCT_CHANGE_AFTER_BASELINE = NO
```

Esto NO demuestra el estado del workspace local ni certifica cambios locales no persistidos.

---

## 3. Primer checkpoint que impide avanzar

**TASK_ID:** `TV-STATE-RECONCILE-001`  
**OBJECTIVE:** verificar el workspace local y reconciliarlo contra la verdad remota/persistida antes de cualquier nuevo cambio de producto.  
**STATUS:** `READY`

**DEPENDENCIES:**
- acceso al repo local real;
- `git status`, branch, HEAD, diff y archivos modificados;
- evidencia de Gate 0C disponible en local;
- no alterar el workspace durante la lectura.

**FIRST_BLOCKER:** el estado local actual no está verificado desde este control plane. Los documentos históricos de estado estaban desalineados con la rama canónica actual.

**ACCEPTANCE:**
1. branch local identificada;
2. HEAD local identificado;
3. working tree clasificado limpio/sucio;
4. divergencia local↔remoto determinada;
5. cambios Gate 0C identificados sin modificarlos;
6. siguiente tarea material seleccionada desde evidencia;
7. ningún PASS declarado sin evidencia física cuando corresponda.

**MINIMUM_TEST:** lectura read-only de Git + inventario de cambios + validación de evidencia existente.

**EVIDENCE_REQUIRED:** salida de `git status`, `git rev-parse HEAD`, branch actual, diff/changed files y artefactos de evidencia relevantes.

**NEXT_EXACT_ACTION:** ejecutar una inspección local READ_ONLY antes de cualquier implementación o sincronización.

---

## 4. Gate de recursos y anti-alucinación

Reglas permanentes:

- hipótesis ≠ hecho;
- test automatizado ≠ comportamiento físico;
- ausencia de evidencia ≠ evidencia negativa;
- no declarar PASS sin evidencia;
- no asumir versiones, compatibilidad, integración ni estado local;
- no crear arquitectura nueva sin blocker demostrado;
- preferir el test mínimo reversible;
- detener intentos repetitivos sin nueva evidencia;
- si falla una verificación, registrar y STOP;
- no promover una tecnología de Radar a implementación sólo por novedad.

Estados de tarea permitidos:

`NOT_TESTED | READY | IN_PROGRESS | FAIL | BLOCKED | PASS | CLOSED`

---

## 5. TaskView

```text
TASKVIEW_ROLE = candidate Execution State / Project Control Plane
TASKVIEW_STATUS = NOT_TESTED
PRODUCTION_CONTROL_PLANE = FALSE
PROMOTION_GATE = TV-001..TV-008
```

Hasta completar TV-001..TV-008, TaskView no es fuente de verdad ni dependencia del proyecto.

Cuando se evalúe deberá cubrir, como mínimo:

- tareas/subtareas;
- dependencias;
- estados;
- historial;
- prioridades;
- ownership;
- permisos;
- API;
- webhooks;
- MCP;
- trazabilidad de ejecución.

---

## 6. Regla de cierre de trabajo material

Toda sesión material debe persistir:

```text
TASK_ID
OBJECTIVE
CURRENT_STATE
DEPENDENCIES
FIRST_FAILURE_OR_BLOCKER
ACCEPTANCE
MINIMUM_TEST
EVIDENCE_REQUIRED
RESULT
NEXT_EXACT_ACTION
```

Destino:

- decisión → ADR / DECISIONS;
- fallo → FAILURE LIBRARY;
- trabajo actual → CURRENT_STATE / TASK STATE;
- lección validada → PLAYBOOK / SKILL;
- evidencia → EVIDENCE ARTIFACT;
- cambio de fuente → FRESHNESS REGISTRY / TES;
- siguiente paso → CURRENT_STATE / TASK STATE.

No dejar continuidad dependiente de memoria del chat.

---

## 7. Regla anti-deriva

No incorporar framework, agente, modelo, base de datos, cola, servicio, protocolo, herramienta o capa de abstracción salvo que:

1. resuelva un blocker actual y demostrado;
2. exista evidencia del problema;
3. una alternativa más simple sea insuficiente;
4. exista criterio de éxito;
5. exista rollback;
6. el costo de recursos esté justificado.

`RADAR != IMPLEMENTATION AUTHORIZATION`.
