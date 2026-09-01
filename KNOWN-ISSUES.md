# TukeVision — Registro de Defectos y Limitaciones Conocidas

Este documento consolida el estado oficial de los defectos y limitaciones operacionales de la plataforma.

---

## 1. Defectos Evaluados

### DEF-OBS-1: Flujo de video activo sin ejecución de inferencia
- **Severidad**: ALTA (Riesgo de silencio operacional).
- **Estado en Fase 8**: `NOT_REPRODUCED` durante la prueba física de soak de 3600 segundos en las 15 cámaras.
- **Mecanismo de Guardia**: Implementado `InferenceCoverageGuard` en `src/pilot/guard.py` que monitorea activamente la relación de fotogramas recibidos versus inferencias ejecutadas, levantando el estado `ACTIVE_CAMERA_WITHOUT_INFERENCE` si un canal se congela sin ejecutar modelos.

### DEF-F5-001 / DEF-F5-002: Tolerancia de hechos no soportados en el validador
- **Estado**: `CLOSED` & `VERIFIED`. El validador `AgentOutputValidator` rechaza estrictamente cualquier hecho con `unsupported_facts > 0` provocando fallback determinista inmediato.

### DEF-F7-001: Evaluación prematura de evidencia en acciones de bajo riesgo
- **Estado**: `CLOSED` & `VERIFIED`. `ActionEvidenceGate` evalúa la suficiencia de evidencia antes de permitir cualquier ejecución bajo `AUTONOMY_2`.

---

## 2. Limitaciones Operacionales Formalizadas

1. **Autonomía 3 Deshabilitada (`AUTONOMY_3_ENABLED=false`)**:
   - Acciones que afecten infraestructura física, credenciales o comunicaciones externas están estrictamente bloqueadas.
2. **Ausencia de Identificación Biométrica**:
   - La plataforma rastrea entidades temporales (`TemporalEntityState`) y homografía de coordenadas. No se genera perfilamiento persistente ni reconocimiento facial.
3. **Dependencia de Calibración Espacial**:
   - Las transiciones de cámara (`Handoff`) requieren calibración de plano y vistas (`viewshed`). Las cámaras no calibradas operan en modo de detección aislada sin correlación cruzada.
