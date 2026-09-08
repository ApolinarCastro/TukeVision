# TukeVision — Technical Evolution System (TES) & Plan Maestro V3

El **Technical Evolution System (TES)** es el marco canónico de gobernanza técnica, trazabilidad, aprendizaje acumulado y estado de madurez de TukeVision V3.

---

## 1. Regla Permanente de Cierre Técnico

> **NO MATERIAL CHANGE IS COMPLETE UNTIL:**  
> `CODE + TEST + DOCS + TES RECONCILIATION ARE CONSISTENT`

Toda adición, adaptación, integración, rechazo tecnológico, cambio en la madurez de una capacidad, decisión de arquitectura o certificación física debe reflejarse sincrónicamente en esta estructura antes de considerar cerrado cualquier macro ciclo.

---

## 2. TES-FIRST — Consulta obligatoria antes de inventar una solución

Ante cualquier defecto, regresión, cuello de botella o necesidad técnica, la primera acción de ingeniería es consultar TES antes de diseñar una solución nueva.

```text
PROBLEMA REAL
→ BUSCAR EN EXPERIENCE_STORE
→ BUSCAR EN TECHNOLOGY_RADAR
→ BUSCAR EN DECISION_LOG / RADAR_RECONCILIATION
→ IDENTIFICAR EXPERIENCIA RELACIONADA
→ REUTILIZAR / ADAPTAR / BENCHMARK / RECHAZAR
→ SOLO SI NO EXISTE PATRÓN SUFICIENTE: INVESTIGAR FUERA
→ RESOLVER
→ TEST DE REGRESIÓN
→ ACTUALIZAR TES
```

Reglas:

- `TES_CONSULTED=YES` es obligatorio antes de proponer un módulo, dependencia, algoritmo o arquitectura nueva para un problema ya observado.
- Una experiencia documentada no puede quedar indefinidamente como conocimiento pasivo si coincide con una brecha real del sistema.
- Si una experiencia externa resuelve el mismo problema, debe compararse contra el baseline actual antes de reinventar.
- TES no sustituye evidencia. Una experiencia puede orientar una solución; la adopción se decide por pruebas y compatibilidad arquitectónica.

---

## 3. Ciclo activo de evaluación de experiencias

Toda experiencia material usa este ciclo:

```text
DISCOVERED
→ VERIFIED
→ MAPPED_TO_TUKEVISION
→ ACTIVE_EVALUATION
→ BENCHMARKED
→ ADAPT | INTEGRATE | RESERVE | REJECT | ALREADY_RESOLVED
→ IMPLEMENTED (si aplica)
→ VALIDATED
→ PERIODIC_REVIEW
```

### Regla anti-dormancia

Una experiencia con estado `EVALUATE`, `WATCH`, `BENCHMARK`, `TARGET` o equivalente entra automáticamente en la **cola activa del Radar**. No debe desaparecer del proceso por haber sido documentada.

Cada elemento activo debe conservar:

- problema que resuelve;
- componente TukeVision relacionado;
- estado actual;
- evidencia o benchmark disponible;
- coste/riesgo/licencia;
- `REVISIT_WHEN`;
- decisión siguiente.

Cuando aparezca un problema nuevo, el Radar debe elevar primero las experiencias cuya `REVISIT_WHEN` coincida con ese problema.

---

## 4. Estructura de Gobernanza Canónica

| Documento | Propósito |
| :--- | :--- |
| **[PLAN_MAESTRO_V3.md](PLAN_MAESTRO_V3.md)** | Hoja de ruta estratégica, estados formales de madurez y arquitectura consolidada. |
| **[CAPABILITY_MATRIX.md](CAPABILITY_MATRIX.md)** | Matriz detallada de trazabilidad código ↔ prueba ↔ evidencia física por capacidad. |
| **[DECISION_LOG.md](DECISION_LOG.md)** | Registro inmutable de decisiones arquitectónicas y tecnológicas materiales. |
| **[EXPERIENCE_STORE.md](EXPERIENCE_STORE.md)** | Memoria operacional y de ingeniería: problema → patrón → decisión → resultado. |
| **[TECHNOLOGY_RADAR.md](TECHNOLOGY_RADAR.md)** | Radar activo: `ADOPT`, `ADAPT`, `ACTIVE_EVALUATION`, `WATCH`, `RESERVE`, `REJECT`. |
| **[06_Research/RADAR_RECONCILIATION.md](06_Research/RADAR_RECONCILIATION.md)** | Inventario reconciliado de experiencias y candidatas, incluidas las antiguamente dormidas. |

---

## 5. Principio de Verdad Epistémica

El TES describe el estado real demostrable del sistema. No es evidencia por sí mismo ni sustituye a las pruebas físicas:

```text
TES CLAIM → CODE → TEST → PHYSICAL EVIDENCE (WHEN REQUIRED)
```

El Radar tampoco autoriza integración automática:

```text
EXPERIENCE
→ EVIDENCE
→ BENCHMARK
→ DECISION
```

No:

```text
EXPERIENCE
→ ENTHUSIASM
→ CORE CHANGE
```

---

## 6. Cierre obligatorio de aprendizaje

Todo defecto material debe cerrar con:

```text
FAILURE
→ ROOT_CAUSE
→ CORRECTION
→ REGRESSION_TEST
→ EXPERIENCE_RECORD
→ RADAR/DECISION UPDATE
```

Objetivo permanente: **no repetir investigación ni reconstruir desde cero una solución que TukeVision ya aprendió.**
