# TukeVision — Technical Evolution System (TES) & Plan Maestro V3

El **Technical Evolution System (TES)** es el marco canónico de gobernanza técnica, trazabilidad, experiencia reutilizable y estado de madurez de TukeVision V3.

---

## 1. Regla Permanente de Cierre Técnico

> **NO MATERIAL CHANGE IS COMPLETE UNTIL:**  
> `CODE + TEST + DOCS + TES RECONCILIATION ARE CONSISTENT`

Toda adición, adaptación, integración, rechazo tecnológico, cambio en la madurez de una capacidad, decisión de arquitectura o certificación física debe reflejarse sincrónicamente en esta estructura antes de considerar cerrado cualquier macro ciclo.

---

## 2. Regla Permanente de Consulta Antes de Inventar

Desde 2026-09-08 el TES es **consulta obligatoria para resolución de problemas**.

```text
PROBLEMA
→ TES SEARCH
→ EXPERIENCE STORE
→ KNOWLEDGE SOURCE INDEX
→ DECISION LOG
→ TECHNOLOGY RADAR
→ REUTILIZAR / ADAPTAR / BENCHMARK / INTEGRAR
→ sólo entonces diseñar algo nuevo
```

`TES_SEARCH_SKIPPED = CHANGE_NOT_READY`.

El objetivo es convertir experiencia acumulada en velocidad de desarrollo y evitar el ciclo:

`INVENTAR → FALLAR → PARCHEAR → REDESCUBRIR`.

La regla operativa completa está en [ACTIVE_EVALUATION_PROTOCOL.md](ACTIVE_EVALUATION_PROTOCOL.md).

---

## 3. Estructura de Gobernanza Canónica

| Documento | Propósito |
| :--- | :--- |
| **[PLAN_MAESTRO_V3.md](PLAN_MAESTRO_V3.md)** | Hoja de ruta estratégica, estados formales de madurez y arquitectura consolidada. |
| **[CAPABILITY_MATRIX.md](CAPABILITY_MATRIX.md)** | Matriz detallada de trazabilidad código ↔ prueba ↔ evidencia física por capacidad. |
| **[DECISION_LOG.md](DECISION_LOG.md)** | Registro inmutable de decisiones arquitectónicas y tecnológicas materiales. |
| **[TECHNOLOGY_RADAR.md](TECHNOLOGY_RADAR.md)** | Evaluación de tecnologías y patrones: `ADOPT`, `ADAPT`, `EVALUATE`, `WATCH`, `RESERVE`, `REJECT`. |
| **[EXPERIENCE_STORE.md](EXPERIENCE_STORE.md)** | Problemas, patrones, resultados, fallos y aprendizajes reutilizables. |
| **[KNOWLEDGE_SOURCE_INDEX.md](KNOWLEDGE_SOURCE_INDEX.md)** | Índice canónico de fuentes externas/internas, estado de frescura, mapeo y condición de reevaluación. |
| **[ACTIVE_EVALUATION_PROTOCOL.md](ACTIVE_EVALUATION_PROTOCOL.md)** | Protocolo expedito para activar experiencias dormidas y evaluar sin abrir proyectos paralelos. |

---

## 4. Ciclo Activo de Conocimiento

Una experiencia material no termina al ser documentada:

```text
DISCOVERED
→ VERIFIED
→ MAPPED_TO_TUKEVISION
→ ACTIVE_EVALUATION
→ BENCHMARKED
→ DECIDED
→ ADAPTED / INTEGRATED / WATCH / RESERVED / REJECTED
```

Las experiencias en `EVALUATE`, `WATCH` o `TARGET` deben tener una condición explícita de reevaluación. Si pueden resolver un defecto actual o acelerar el siguiente value slice, pasan a `ACTIVE_EVALUATION`.

---

## 5. Principio de Verdad Epistémica

El TES describe el estado real demostrable del sistema. No es evidencia por sí mismo ni sustituye a las pruebas físicas:

```text
TES CLAIM → CODE → TEST → PHYSICAL EVIDENCE (WHEN REQUIRED)
```

También aplica:

```text
KNOWLEDGE ≠ DEPENDENCY
BENCHMARK ≠ ADOPTION
ADAPT_PATTERN ≠ COPY_CODE
DOCUMENTED ≠ IMPLEMENTED
```

---

## 6. Regla de Frescura de Fuentes

Cuando una fuente registrada pueda resolver un problema actual, sea tocado el subsistema relacionado o exista una actualización upstream material, debe revisarse primero la fuente original y después reconciliarse el TES.

Para repositorios GitHub, verificar al menos: actividad/release relevante, documentación vigente, licencia, cambios materiales y condición de adopción.

No se incorpora código externo al core sin revisión de licencia y provenance.
