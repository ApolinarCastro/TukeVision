# Protocolo Activo de Evaluación — TES V3

**STATUS:** ACTIVE
**DATE:** 2026-09-08
**SCOPE:** conocimiento técnico, experiencia externa/interna, resolución de problemas y radar tecnológico.

## 1. Regla operativa obligatoria

Antes de diseñar una solución nueva, modificar arquitectura o incorporar otra dependencia, TukeVision debe consultar el TES.

```text
PROBLEMA REAL
→ TES SEARCH
→ EXPERIENCIAS RELACIONADAS
→ EVIDENCIA / PATRÓN / LIMITACIÓN
→ YA_RESUELTO | ADAPTAR | BENCHMARK | INTEGRAR | RECHAZAR
→ IMPLEMENTAR SÓLO LA BRECHA REAL
```

`TES_SEARCH_SKIPPED = CHANGE_NOT_READY`.

El TES no es archivo histórico pasivo. Es la primera fuente interna de consulta para evitar reinventar soluciones, repetir fallos y abrir módulos duplicados.

## 2. Ciclo de vida de una experiencia

Toda experiencia material debe transitar por estados explícitos:

```text
DISCOVERED
→ VERIFIED
→ MAPPED_TO_TUKEVISION
→ ACTIVE_EVALUATION
→ BENCHMARKED
→ DECIDED
→ ADAPTED | INTEGRATED | WATCH | RESERVED | REJECTED
→ VALIDATED cuando aplique
```

Una fuente no puede permanecer indefinidamente en `DISCOVERED`, `EVALUATE` o `WATCH` sin condición de reevaluación.

## 3. Activación de experiencias dormidas

Desde 2026-09-08 todas las experiencias registradas en TES que no estén `ADOPTED`, `ADAPTED`, `REJECTED` o `RESERVED` con condición clara pasan a la **cola activa de evaluación**.

Prioridad:

- `P0-ACTIVE`: puede resolver defectos o capacidades actuales.
- `P1-ACTIVE`: puede acelerar el siguiente value slice.
- `CONDITIONAL`: se evalúa cuando aparece la condición técnica definida.
- `RESERVE`: no consume tiempo activo hasta que cambie el contexto.

## 4. Evaluación expedita

Una evaluación debe ser pequeña y decisiva. No crear proyectos paralelos para evaluar una experiencia.

Cada candidato debe responder:

1. ¿Qué problema real de TukeVision resuelve?
2. ¿Qué componente existente toca o reemplaza?
3. ¿Existe ya capacidad equivalente?
4. ¿Qué evidencia externa respalda el patrón?
5. ¿Qué licencia o restricción aplica?
6. ¿Qué benchmark mínimo decide?
7. ¿Qué métrica debe superar al baseline?
8. ¿Qué riesgo/regresión introduce?
9. ¿Cuál es la decisión final?

Salida válida:

`YA_RESUELTO | ADAPTAR | INTEGRAR | BENCHMARK_MÁS | WATCH | RESERVE | REJECT`.

## 5. Regla de aceleración

Priorizar experiencias que permitan:

```text
1 PATRÓN
→ VARIAS CAPACIDADES MEJORADAS
```

Ejemplos de alto apalancamiento:

- resiliencia RTSP / lifecycle;
- tracking temporal / recovery;
- percepción selectiva;
- evidencia e investigación semántica;
- provenance / integridad;
- seguridad de agentes;
- conectividad multimodal neutral de proveedor.

## 6. Actualización desde GitHub y GitLab

GitHub y GitLab son **fuentes de ingeniería de primera clase y equivalentes para el radar TES**. Ninguna de las dos debe tratarse como secundaria por defecto.

Para repositorios registrados en cualquiera de ambas forjas, cada reevaluación debe comprobar como mínimo:

- repositorio canónico original;
- forge de origen: `GITHUB` o `GITLAB`;
- actividad reciente / releases / tags cuando existan;
- README y documentación vigente;
- licencia;
- cambios materiales en arquitectura o capacidades;
- issues, merge requests, milestones o restricciones relevantes cuando afecten la decisión;
- commit, tag o release observado cuando la decisión dependa de una versión;
- relación `CANONICAL_UPSTREAM / MIRROR / FORK` cuando el mismo proyecto exista en más de una forja.

Reglas:

```text
GITHUB_SOURCE != MORE_AUTHORITATIVE_BY_DEFAULT
GITLAB_SOURCE != SECONDARY_BY_DEFAULT
CANONICAL_UPSTREAM = SOURCE_OF_TRUTH
MIRROR != CANONICAL_UNLESS_PROVEN
```

Si una experiencia existe en GitHub y GitLab:

1. identificar cuál es el upstream canónico;
2. registrar ambas URLs cuando aporten valor;
3. no duplicar Experience Records por espejo;
4. comparar divergencias materiales sólo cuando existan;
5. conservar provenance de la fuente concreta usada para una decisión.

No copiar código de terceros al core sin revisión explícita de licencia y provenance.

## 7. Consulta obligatoria ante fallos

Ante un defecto o bloqueo:

```text
FAILURE
→ TES SEARCH(problem, subsystem, symptom)
→ EXPERIENCE_MATCHES
→ DECISION_LOG
→ EXISTING_TESTS
→ ONLY THEN NEW DESIGN
```

Toda corrección material debe registrar qué experiencia fue consultada o declarar `NO_RELEVANT_EXPERIENCE_FOUND`.

## 8. No duplicación

Antes de crear un módulo:

`SEARCH_EXISTING_CAPABILITY`.

Resultado obligatorio:

- `EXISTS_USE_IT`
- `EXTEND_EXISTING`
- `NEW_JUSTIFIED`

## 9. Frontera entre conocimiento y producto

Registrar una experiencia NO significa incorporarla automáticamente.

```text
KNOWLEDGE ≠ DEPENDENCY
BENCHMARK ≠ ADOPTION
ADAPT_PATTERN ≠ COPY_CODE
DOCUMENTED ≠ IMPLEMENTED
```

## 10. Mantenimiento

Los documentos canónicos para este proceso son:

- `TECHNOLOGY_RADAR.md`
- `EXPERIENCE_STORE.md`
- `KNOWLEDGE_SOURCE_INDEX.md`
- `ACTIVE_EVALUATION_PROTOCOL.md`
- `DECISION_LOG.md`
- `CAPABILITY_MATRIX.md`

Cada actualización material de radar debe reconciliar estos documentos y evitar estados contradictorios.

Las revisiones periódicas del radar deben consultar **GitHub y GitLab** antes de declarar `NO_CHANGE` para una categoría técnica relevante, salvo que exista una razón documentada por la cual una de las forjas no aplique a esa categoría.
