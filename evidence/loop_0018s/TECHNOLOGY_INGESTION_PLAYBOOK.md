# TECHNOLOGY_INGESTION_PLAYBOOK

**Documento permanente de TukeVision** · **Versión:** 1.0 · **LOOP de creación:** 0018S (2026-08-16)
**Aplica a:** toda tecnología, dependencia, librería, modelo, binario o patrón externo que se proponga incorporar a BASE, portable o al roadmap.
**Baseline certificado de referencia:** Python 3.12, OpenCV 5.0.0.93, Ultralytics 8.4.115 + YOLO11n (CPU), ByteTrack (trackers 2.5.0.post0), Supervision 0.29.1 (uso mínimo `sv.Detections`), Tkinter 8.6, JSON local; 359/359 tests, `NEW_DEPENDENCIES=0`, commit `cfad931` (16-08-2026). [HECHO: worker_90, worker_92]

## 0. Propósito

TukeVision recibe propuestas tecnológicas de fuentes múltiples (radar tecnológico, solicitudes del usuario, investigación externa, experimentos portable). Sin un proceso formal, el riesgo es: copiar repositorios completos al Core, agregar dependencias sin necesidad demostrada, romper el núcleo certificado o perder la trazabilidad de la decisión. **Este playbook fija el flujo exacto de 13 pasos por el que TODA tecnología futura debe pasar antes de tocar BASE.** Ninguna excepción: la tecnología que no pase el flujo queda en RADAR/DEFER, no en el código.

**Principio rector:** el núcleo certificado (SPEC-0001, E-01 COMPAT, 359/359) es sagrado; todo lo nuevo entra por adaptadores detrás de interfaces estables (ver EXTENSION_BOUNDARIES) o no entra.

## 1. Visión general del flujo de 13 pasos

```
1  GAP_EXISTS? ──NO──► RADAR/DEFER (con trigger)
   │SÍ
2  BASE_ALREADY_SOLVES_IT? ──SÍ──► NO INTEGRATION (registrar ALREADY_COVERED)
   │NO
3  MATURE_SOLUTION_EXISTS? ──NO──► CUSTOM_DEVELOPMENT_REQUIRED (exige evidencia §0 de ZERO-REWRITE)
   │SÍ
4  VERIFICAR licencia · mantenimiento · dependencias · seguridad · hardware
5  POC AISLADO fuera del Core (sandbox removible)
6  MEDIR contra baseline real (tests · fps · memoria · NEW_DEPENDENCIES)
7  ¿Aporta valor? ──NO──► DEFER/REJECT con evidencia de medición
   │SÍ
8  ADAPTER detrás de interfaz estable (nunca mezclado con RTSP/SourceManager)
9  FOCUSED TESTS
10 FULL REGRESSION (≥ baseline; NEW_DEPENDENCIES=0 salvo aprobación)
11 PHYSICAL VALIDATION (solo cuando corresponda)
12 COMMIT BASE
13 ACTUALIZAR TES + RETIRAR POC + reglas ANTI-LOOP
```

Los pasos 1–7 son de **decisión y experimentación** (no tocan BASE). Los pasos 8–13 son de **integración** (tocan BASE solo por commit aprobado del flujo). Cualquier paso puede devolver la tecnología a DEFER/REJECT sin culpa: DEFER con trigger es un resultado válido.

## 2. Detalle de cada paso

### Paso 1 — GAP_EXISTS?

**Definición.** Determinar si existe un gap REAL y documentado del producto actual que la tecnología candidata resolvería. "Gap real" = síntoma reportado por el usuario, brecha en la capability matrix certificada, o fila del radar con `REAL_TUKEVISION_GAP` explícito. Los gaps se verifican contra el estado REAL (worker tipo worker_90), no contra diseño ni conversaciones: conversaciones y planes NO son evidencia. [HECHO: worker_90 §0]

**Criterio de entrada.** Tecnología candidata propuesta (fila de radar, solicitud del usuario, hallazgo de investigación).

**Criterio de salida (DoD).**
- Decisión binaria `GAP_EXISTS=SI/NO` escrita, con referencia al gap (capability matrix fila + estado, o síntoma reportado).
- Si `NO` → el ítem pasa a `RADAR/DEFER` con trigger escrito y motivo; NO continúa.
- Si `SI` → se documenta el gap en una línea ("el gap que esta tecnología cierra es…") y se pasa al paso 2.

### Paso 2 — BASE_ALREADY_SOLVES_IT?

**Definición.** Verificar si el código certificado de BASE (o una extensión interna reutilizable) ya resuelve el gap, en todo o en parte. Se inspecciona: `src/` (archivo:línea), tests que pasan, DECs vigentes, `src/temporal/`, extensiones portable E-02/E-04/E-05 clasificadas (REUSABLE_WITH_ADAPTATION / REQUIRES_DECISION), `REUSE_MAP_E02.md`.

**Criterio de entrada.** `GAP_EXISTS=SI`.

**Criterio de salida (DoD).**
- Decisión `BASE_ALREADY_SOLVES_IT=SI/NO` con evidencia concreta (módulo + test + loop, o "NO_EXISTE" en la capability matrix).
- Si `SÍ` → **NO INTEGRATION**: se registra `ALREADY_COVERED` en la matriz de decisión y el flujo termina aquí (ej.: Mosaic → DEC-0004; arquitectura event/evidence → motores propios certificados). [HECHO: worker_92 matriz — 7 ítems ALREADY_COVERED]
- Si `NO` pero hay base parcial reutilizable (ej.: `src/temporal/` para dedup, E-02 para conteo) → se registra `WHAT_WE_CAN_REUSE` y se continúa.

### Paso 3 — MATURE_SOLUTION_EXISTS?

**Definición.** Buscar si existe una solución externa madura (librería, estándar, patrón verificado) para el gap. **Regla:** si existe → adapter/plugin/interface ANTES que desarrollo custom. Madurez = mantenimiento activo verificado, adopción razonable, sin EOL conocido, compatible con el stack (Python 3.12, Windows, CPU).

**Criterio de entrada.** `BASE_ALREADY_SOLVES_IT=NO`.

**Criterio de salida (DoD).**
- Decisión `MATURE_SOLUTION_EXISTS=SI/NO` con la(s) opción(es) identificada(s) y su estado de madurez (fecha de último release, mantenimiento, licencia preliminar).
- Si `SÍ` → se continúa con la solución como candidata a adapter.
- Si `NO` → se invoca `CUSTOM_DEVELOPMENT_REQUIRED` (ver ZERO-REWRITE POLICY): desarrollo custom solo con evidencia escrita de que (1) reuso BASE/portable/TES y (2) extensión mature NO resuelven el gap. Sin esa evidencia, DEFER.

### Paso 4 — Verificación de licencia, mantenimiento, dependencias, seguridad, hardware

**Definición.** Cinco verificaciones formales antes de cualquier POC. Usar el checklist de §3.1 y dejar cada respuesta con evidencia (URL de licencia, fecha de release, árbol de dependencias, resultado de escaneo, presupuesto de cómputo).

**Criterio de entrada.** Solución mature identificada (o custom justificado).

**Criterio de salida (DoD).**
- Checklist completo (5 sub-checks) firmado con evidencia y veredicto por sub-check: `OK / CON RIESGO (mitigación) / BLOQUEANTE`.
- `LICENSE_RISK`, `DEPENDENCIES` (¿rompe `requirements.lock.txt`?), `CPU_GPU_COST`, `ARCHITECTURAL_RISK` quedan escritos con la misma granularidad de la matriz de decisión del radar (15 campos).
- Cualquier `BLOQUEANTE` sin mitigación → DEFER/REJECT con motivo. (Ej. real: ReID/embeddings = conflicto de gobernanza DEC-0013/0019/0036 → DEFER; Faceplugin/Warden y Qwen = REJECT por gobernanza/política. [HECHO: worker_92])

### Paso 5 — POC AISLADO fuera del Core

**Definición.** Ejecutar una prueba de concepto AISLADA, **fuera de `src/` de BASE**, en el sandbox designado (ver §3.2). El POC nunca se escribe dentro del pipeline de producto ni se importa desde `src/`. Su propósito: validar hipótesis técnicas sin contaminar el núcleo certificado.

**Criterio de entrada.** Checklist del paso 4 sin bloqueantes, o bloqueantes con mitigación aceptada explícitamente.

**Criterio de salida (DoD).**
- POC ejecutado en la ruta sandbox con resultados documentados (métricas, artefactos, comandos).
- Criterio de `REMOVABLE` verificado: borrar el sandbox por completo deja BASE intacto (git status del BASE limpio salvo evidencia; 0 archivos nuevos fuera del sandbox; ver §3.2).
- Si el POC no se puede ejecutar ahora por una condición no resuelta (aprobación pendiente, hardware, decisión de producto) → **POC aislado CONDICIONADO**: se documenta el diseño del POC y el trigger que lo habilita, y el ítem queda DEFER hasta que el trigger se cumpla. (Ej.: ONVIF, §5.2.)

### Paso 6 — Medir contra baseline real

**Definición.** Comparar el POC contra el baseline certificado usando la plantilla de §3.3: regresión de tests del área, fps medidos (referencia: 54.5 ms/frame YOLO11n CPU [HECHO: worker_92]), memoria (referencia: 227.8→232.4 MB estable en 4 cámaras físicas [HECHO: worker_90]), y `NEW_DEPENDENCIES` (referencia: 0 en loops 0018N–R [HECHO: worker_92]).

**Criterio de entrada.** POC aislado ejecutado.

**Criterio de salida (DoD).**
- Tabla de medición completa (tests · fps · memoria · NEW_DEPENDENCIES) con la del POC y la del baseline lado a lado.
- Veredicto `APORTA_VALOR=SI/NO` con números.

### Paso 7 — ¿Aporta valor? → Decisión

**Definición.** Con la medición del paso 6, decidir ingesta o no.

**Criterio de salida (DoD).**
- `SI` → pasar al paso 8 con el adapter definido.
- `NO` → `DEFER` (con trigger) o `REJECT` (con motivo), documentando por qué la medición no justifica la integración. El POC se retira igualmente (paso 13).
- Toda decisión queda en la matriz del radar; **PENDING sin razón queda prohibido: si no se decide, es DEFER con motivo** [HECHO: worker_92 — 0 PENDING].

### Paso 8 — Adapter detrás de interfaz estable

**Definición.** La tecnología entra a BASE exclusivamente como un adapter que implementa una de las interfaces desacopladas del catálogo de Extension Boundaries (InferenceBackend, TrackingBackend, ActivityBackend, SegmentationBackend, ReIDBackend, EvidenceBackend, DiscoveryBackend, ReasoningBackend). **Prohibido** mezclar la tecnología nueva con RTSP/SourceManager o con el pipeline certificado directamente: el adapter aísla la dependencia y permite reemplazo sin regresión.

**Criterio de entrada.** Decisión `APORTA_VALOR=SI`.

**Criterio de salida (DoD).**
- Adapter escrito detrás de la interfaz estable documentada; el Core depende de la interfaz, no del adapter.
- Cero cambios en el comportamiento del pipeline certificado (E-01/SPEC-0001) por este paso.
- La interfaz NO se crea ad-hoc para la tecnología: se usa la del catálogo, o se extiende el catálogo mediante documento aprobado (nunca como efecto secundario).

### Paso 9 — Focused tests

**Definición.** Tests enfocados del adapter y de su contrato (entradas/salidas, casos límite, fallo de la dependencia externa). Patrón de referencia: focused tests por loop (87/87 live_sources, 39/39 activity, 42/42 inference, 33/33 temporal [HECHO: worker_90]).

**Criterio de salida (DoD).** Tests del adapter escritos y pasando; verificación de que el adapter falla de forma aislada y controlada cuando la tecnología externa falla (no arrastra al Core).

### Paso 10 — Full regression

**Definición.** Ejecutar la regresión completa de BASE y verificar que el conteo es ≥ baseline (hoy 359/359) y que `NEW_DEPENDENCIES` respeta la política (0 salvo aprobación explícita de una dependencia con su justificación).

**Criterio de salida (DoD).**
- Regresión completa PASS con conteo ≥ baseline.
- `NEW_DEPENDENCIES` declarado (0 o la aprobada con motivo).
- Verificación de compile (`py_compile`/`compileall`) y secret scan (0 fugas) como parte del gate (G4/G5 del flujo S).

### Paso 11 — Physical validation (solo cuando corresponda)

**Definición.** Validación física SOLO para cambios que tocan captura real, red, cámaras o comportamiento en runtime con hardware (ej.: reconexión RTSP, multicámara, nuevo modelo sobre video real). No aplica a lógica determinista pura (ej.: filtro de estaticidad) que ya quedó cubierta por tests sintéticos; en ese caso se documenta `NO_APLICA` con justificación.

**Criterio de salida (DoD).** Certificación física documentada (patrón: 300 s/4 cámaras/0 stalls, o el procedimiento del loop correspondiente) con verdict, o `NO_APLICA` justificado. La validación física nunca es prerrequisito del commit cuando el cambio es sintéticamente certificable.

### Paso 12 — Commit BASE

**Definición.** Commit del adapter + tests + evidencia en el repositorio BASE con mensaje siguiendo la convención de loops (`loop-0018X: …`), dejando HEAD verificado y working tree limpio.

**Criterio de salida (DoD).** Commit creado; HEAD y working tree verificados (gate G2); evidencia del loop escrita en `evidence/loop_XXXX/` antes del commit.

### Paso 13 — Actualizar TES + Retirar POC + reglas ANTI-LOOP

**Definición.** (a) Sincronizar TES (registry de tecnología, DEC si aplica, capability matrix, backlog) para que el estado escrito coincida con el estado de código; (b) retirar el POC aislado verificando su removibilidad; (c) aplicar las reglas ANTI-LOOP de §6 antes de cerrar el loop.

**Criterio de salida (DoD).**
- TES actualizado en el punto del checklist correspondiente (registro maestro, decisions o capability matrix).
- Sandbox del POC eliminado y verificada su ausencia de rastros en BASE.
- Reglas ANTI-LOOP revisadas una a una (checklist §6), con especial atención a `EVERY_LOOP_MUST_CHANGE_PRODUCT_STATE` (el loop debe dejar el producto en un estado distinto, aunque sea un DEFER documentado o un POC retirado).

## 3. Plantillas

### 3.1 Checklist de verificación (Paso 4)

```
TECNOLOGÍA CANDIDATA: <nombre> | FECHA: <YYYY-MM-DD> | LOOP: <XXXX> | DECISIÓN PREVIA: GAP=<SI/NO> BASE_SOLVES=<SI/NO> MATURE=<SI/NO>

[ ] 1. LICENCIA
    - Licencia exacta: <p.ej. AGPL-3.0 / MIT / Apache-2.0>
    - Compatible con el modelo de distribución actual (local, sin redistribución): SÍ / NO / REQUIERE_ANÁLISIS
    - Riesgo: BAJA / MEDIA / ALTA — Evidencia: <URL/nombre del archivo de licencia>
[ ] 2. MANTENIMIENTO
    - Último release: <fecha> | Repositorio activo: SÍ / NO / INCIERTO
    - EOL conocido: <fecha o "no"> | Comunidad/adopción: <nota>
[ ] 3. DEPENDENCIAS
    - ¿Agrega dependencias nuevas? SÍ (lista: <…>) / NO
    - ¿Rompe requirements.lock.txt / el lock del venv? SÍ / NO — Si SÍ: justificación obligatoria
    - Compatibilidad: Python <versión> · Windows <SÍ/NO> · arquitectura <x64/…>
[ ] 4. SEGURIDAD
    - ¿Maneja credenciales? ¿Cómo se redactan/loguean? (política: docs/SECRETS_AND_LOCAL_CONFIG.md)
    - ¿Exposición de red? <puertos/URLs> · ¿Requiere redacción ampliada (rtsps/http/keywords)? SÍ/NO
    - Escaneo/vulnerabilidades conocidas: <nota o N/A>
[ ] 5. HARDWARE / CÓMPUTO
    - Presupuesto CPU/GPU estimado (vs. 54.5 ms/frame YOLO11n CPU): <medida o estimación>
    - Memoria estimada (vs. ~230 MB estables en 4 cámaras): <nota>
    - ¿Requiere hardware nuevo? <SÍ/NO — cuál>

VEREDICTO GLOBAL: OK / CON_RIESGO_MITIGADO / BLOQUEANTE — MITIGACIÓN O MOTIVO: <texto>
```

### 3.2 Plantilla de POC aislado (Paso 5)

```
RUTA SANDBOX (fuera de src/ de BASE): <ruta concreta, p.ej. <BASE>/poc/<tecnologia>_<loop>/ o
  <BASE>/sandbox/poc_<nombre>/ — NUNCA dentro de src/, tests/ ni evidence/ del Core>
RÉGIMEN DEL SANDBOX:
  - El POC no se importa desde src/ ni se registra en MANIFEST.json.
  - Sus dependencias (si las hubiera) se instalan SOLO en el entorno del sandbox; jamás en el venv certificado.
  - El sandbox es borrable con un solo comando/gesto y su borrado deja `git status` de BASE limpio
    (salvo la evidencia escrita del loop en evidence/loop_XXXX/).

HIPÓTESIS: <qué se valida exactamente>
ENTRADAS: <dataset/video/config mínimo>
PROCEDIMIENTO: <pasos reproducibles>
MÉTRICAS A CAPTURAR: <tests · fps · memoria · NEW_DEPENDENCIES — plantilla §3.3>
CRITERIO DE REMOVABLE (verificar ANTES de empezar y DESPUÉS de borrar):
  [ ] El sandbox es un directorio autocontenido (sin symlinks ni archivos compartidos con src/)
  [ ] Ningún import del sandbox apunta a src/ (solo lectura de datos de entrada si hace falta)
  [ ] Al borrarlo: git status de BASE = limpio (o solo evidencia del loop) · venv certificado intacto
  [ ] Los artefactos del POC viven en evidence/loop_XXXX/ (o se descartan)
RESULTADO: <datos> | VEREDICTO: <APORTA_VALOR=SI/NO>
```

### 3.3 Plantilla de medición contra baseline (Paso 6)

```
ÁREA AFECTADA: <captura/detección/tracking/observación/inferencia/evidencia/UI/config>
BASELINE CERTIFICADO (fuente): <loop> — tests: <N/NN> · fps: <ms/frame> · memoria: <MB> · NEW_DEPENDENCIES: <N>
   | Métrica                    | Baseline (referencia)        | POC (medido)            | Delta / veredicto |
   | Tests del área (focused)   | <87/87 | 39/39 | 42/42 | 33/33> | <N/NN>                | <OK / regresión>  |
   | fps / latencia por frame   | <54.5 ms YOLO11n CPU>         | <medida>               | <mejora/peor/igual>|
   | Memoria (estable)          | <227.8→232.4 MB 4 cámaras>    | <medida>               | <delta MB>         |
   | NEW_DEPENDENCIES           | 0 (loops 0018N–R)             | <N — cuáles>           | <0 / justificar>   |
VEREDICTO: APORTA_VALOR = SI / NO — JUSTIFICACIÓN: <texto con los números>
```

## 4. Integración con el flujo S de cluster/evidencia

El playbook no opera en el vacío: cada loop del flujo S produce evidencia escrita y roles definidos, y el playbook consume y alimenta esa maquinaria.

- **Dónde vive la evidencia.** BASE: `evidence/loop_XXXX/` (certificaciones, matrices, focused tests, demos, gates). Portable (laboratorio): `LOOP-0018*.md` en raíz + `evidence/loop_0018*/` — la evidencia portable es SOLO laboratorio y no equivale a producto (regla `PORTABLE_IS_NOT_PRODUCT`, §6). Análisis del cluster: `.cluster/tukevision-*/worker_*.md` + `review.md`.
- **Regla de evidencia.** Conversaciones y planes NO son evidencia [HECHO: worker_90 §0]. Solo código (archivo:línea), tests que pasan y documentos escritos en `evidence/` o `LOOP-*.md` cuentan. El playbook cita la evidencia en cada paso (paso 2 y 6 lo exigen explícitamente).
- **Roles por ronda** (patrón LOOP-0018S): radar/capacidades/baseline/portable (ronda 1, SOLO LECTURA) → playbook/prioridades/TES/gates (ronda 2) → revisor adversarial (ronda 3, verifica hechos, números y 0 PENDING). El resultado del playbook (este documento) es un entregable del loop y queda en `evidence/loop_0018s/TECHNOLOGY_INGESTION_PLAYBOOK.md`; las matrices de decisión por tecnología viven en `technology_radar.md` + `external_experience_ingestion_matrix.md` del mismo loop.
- **Gates que el flujo debe cumplir** (patrón LOOP-0018S): G8 (100 % tecnologías mapeadas), G9 (cada tecnología con gap o DEFER/REJECT), G10 (playbook completo), G11 (zero-rewrite), G16 (0 dependencias nuevas), G17 (0 reescrituras). Un loop de ingesta no se cierra sin estos gates verificados por el revisor.
- **Ritmo:** el playbook es permanente; las matrices del radar se re-validan en cada loop de ingesta (o cuando el usuario propone tecnología nueva). El estado del estudio de cada tecnología (CERTIFICADO / ESTUDIO COMPLETO / ESTUDIO PARCIAL / DISEÑADO / SIN ESTUDIO) se actualiza en TES al cerrar cada paso relevante.

## 5. Ejemplos concretos aplicados al radar de LOOP-0018S

### 5.1 Personas vs maniquíes — EXTENSION_CANDIDATE P1 (filtro de estaticidad / HumanVerifier)

- **Paso 1 (GAP):** SI. Maniquí entra al conteo y dispara PERMANENCIA_PROLONGADA falsa (dwell→∞) en retail (Nicopoly). [HECHO: worker_92 fila 23; diseño completo worker_60/61/62]
- **Paso 2 (BASE):** NO lo resuelve: `person_detector.py` filtra solo por clase/conf (clase COCO 0); `_stay_seconds` calcula dwell pero no distingue maniquí. Reuso parcial: `src/temporal/` (track local) y `_stay_seconds` sirven de entrada al filtro.
- **Paso 3 (MATURE):** NO existe solución external madura específica (YOLO no distingue maniquíes; no hay librería madura de HumanVerifier) → camino `CUSTOM_DEVELOPMENT_REQUIRED` con evidencia: el diseño propio (máquina de estados UNKNOWN→MOVING/STATIC_SUSPECT/STATIC_CLEARED; "si alguna vez se movió, jamás es maniquí") es O(1), <1–5 ms/frame, 0 dependencias, 24–34 h. [HECHO: worker_92 fila 23]
- **Paso 4 (Verificación):** 0 dependencias → no rompe lock; sin red → sin superficie de seguridad; coste CPU despreciable (<1–5 ms/frame vs 54.5 ms detección); licencia N/A (código propio). Veredicto: OK.
- **Paso 5 (POC):** sandbox `<BASE>/sandbox/poc_human_verifier_0018s/` (o equivalente) con modo tag para calibrar umbrales (90 s + probation) sobre video real del piloto; verificable REMOVABLE.
- **Paso 6 (Medición):** tests focused del filtro + regresión de la cadena de conteo; fps: delta <1–5 ms; memoria: despreciable; NEW_DEPENDENCIES=0.
- **Paso 7 (Valor):** SI — elimina falsos conteos y falsas alertas; directo al piloto Nicopoly.
- **Paso 8 (Adapter):** `src/context/human_verifier.py` (o equivalente) como gate post-tracking/pre-conteo detrás de la cadena de observación — aditivo con `exclude_tracks`; no toca E-01 ni SourceManager.
- **Pasos 9–12:** focused tests → regresión 359/359 → physical NO_APLICA (lógica determinista sintéticamente certificable; validación física del efecto sobre el video real del piloto cuando haya video, documentable como validación opcional) → commit `loop-0018X: mannequin filter`.
- **Paso 13:** TES (capability matrix persona-vs-maniquí: DISEÑADO → CERTIFICADO; registry) + retirar POC + ANTI-LOOP.

### 5.2 ONVIF (WS-Discovery + PTZ) — DEFER P3 con POC aislado CONDICIONADO

- **Paso 1 (GAP):** SI documentado (sin discovery — URL se teclea; sin PTZ — panel decorativo; matriz: ONVIF/discovery/PTZ NO_EXISTE). [HECHO: worker_92 fila 11]
- **Paso 2 (BASE):** NO — NO_EXISTE en BASE; el selector de canal/subtype es manual.
- **Paso 3 (MATURE):** SÍ existe solución external (`python-onvif-zeep`) — pero con riesgos reales.
- **Paso 4 (Verificación):** dependencia nueva rompe `requirements.lock.txt`; soporte ONVIF irregular entre vendedores (riesgo alto en Recording Search); requiere confirmación de capacidades del DVR del piloto; sin caso de negocio aprobado ("Sin gap autorizado", PRIO 7). Veredicto: CON_RIESGO.
- **Paso 5 (POC CONDICIONADO):** el POC aislado NO se ejecuta hoy. Se documenta el diseño (módulo `src/discovery/` + panel PTZ, detrás de SourceManager/controller, cliente HTTP Digest propio como alternativa sin dependencia) y el **trigger** que lo habilita: (1) decisión de producto aprobando discovery/PTZ como feature; (2) confirmación de capacidades ONVIF del dispositivo del piloto. Mientras el trigger no se cumpla → DEFER P3. [HECHO: worker_92 fila 11 — DEFER P3, "POC aislado (solo tras aprobación)"]
- **Pasos 6–13:** se ejecutan solo al cumplirse el trigger; el paso 4 se re-ejecuta antes del POC (el mundo de ONVIF cambia). Hasta entonces, el estado del estudio es ESTUDIO PARCIAL — DISEÑADO.

### 5.3 People flow (conteo IN/OUT/INSIDE) — EXTENSION_CANDIDATE P1 vía adapter de E-02

- **Paso 1 (GAP):** SI reportado por el usuario: doble conteo (misma persona contada N veces). [HECHO: worker_92 fila 18, worker_30 caminos A/B/C]
- **Paso 2 (BASE):** NO del todo. Causa raíz documentada: `track_id` efímero (ByteTrack buffer 30 frames) → doble conteo en re-entradas. BASE resuelve parte con `src/temporal/` (dedup local no biométrico, DEC-0036, 33/33 tests); el conteo por zona no existe en BASE (E-02 solo portable, EXPERIMENTAL).
- **Paso 3 (MATURE):** NO se adopta librería external de conteo; existe reuso interno maduro: E-02 FlowCounter/TrackTrajectory (portable, clasificado REUSABLE_WITH_ADAPTATION [HECHO: worker_92 fila 34]) + `src/temporal/` certificado.
- **Paso 4 (Verificación):** 0 dependencias nuevas (adaptación de código propio); sin riesgo de licencia; coste bajo; riesgo arquitectónico bajo (reuso, no toca E-01). OK.
- **Paso 5 (POC):** sandbox con E-02 adaptado a multicámara; validar dedup por ventana de re-entrada (≥30 s) sin biometría (índice por track local + ventana temporal, NUNCA por identity_id — DEC-0036). REMOVABLE.
- **Paso 6 (Medición):** focused tests de contadores únicos por visita; fps/memoria: delta bajo; NEW_DEPENDENCIES=0.
- **Paso 7 (Valor):** SI — corrige el síntoma reportado por el usuario.
- **Paso 8 (Adapter):** adaptación detrás de SourceManager y de la interfaz Tracking/Observation correspondiente, sin mezclar con RTSP.
- **Pasos 9–13:** focused → regresión → física solo si toca multicámara real (opcional, sintético suficiente en v1) → commit → TES + retiro de POC.

## 6. Regla ANTI-LOOP (Fase 13)

Checklist obligatorio al cerrar cualquier loop de ingesta. Cada regla se verifica explícitamente (SÍ/NO + nota); una violación no resuelta bloquea el cierre del loop.

| # | Regla | Significado operativo | Verificación |
|---|---|---|---|
| 1 | **NO_NEW_AUDIT_WITHOUT_DECISION_OUTPUT** | Ninguna auditoría/investigación nueva se abre sin que la anterior haya producido una decisión (ingestar, DEFER con trigger o REJECT). Auditar por auditar = loop infinito. | Última auditoría del área tiene decisión escrita en matriz/radar. |
| 2 | **NO_NEW_TECH_WITHOUT_REAL_GAP** | Prohibido proponer/instalar tecnología sin `GAP_EXISTS=SI` verificado (paso 1). Sin gap → RADAR/DEFER. | Fila de radar con `REAL_TUKEVISION_GAP` explícito o DEFER con motivo. |
| 3 | **REUSE_BEFORE_CUSTOM_DEVELOPMENT** | Antes de desarrollar: (1) reusar BASE/portable/TES, (2) buscar extensión mature; solo entonces custom (paso 3). | Sección "What we can reuse" completada en la matriz. |
| 4 | **NO_REWRITE_OF_CERTIFIED_COMPONENTS_WITHOUT_REGRESSION** | Nada certificado (E-01, SPEC-0001, módulos con tests) se reescribe sin regresión completa que lo avale (paso 10). | Diff del cambio + regresión ≥359/359. |
| 5 | **ONE_PRODUCT_BASE** | Un solo repositorio de producto (BASE). Portable es laboratorio; dist se regenera del BASE. Prohibido mantener dos "productos" divergentes. | Cambios de producto solo en BASE; dist ≥ HEAD del BASE. |
| 6 | **PORTABLE_IS_NOT_PRODUCT** | Las extensiones EXPERIMENTALES del portable (E-02/E-03/E-04/E-05) no son capacidades del producto hasta migrar por este playbook. [HECHO: worker_92 fila 34] | Capability matrix del BASE marca EXPERIMENTAL_PORTABLE_ONLY hasta ingesta. |
| 7 | **EVERY_LOOP_MUST_CHANGE_PRODUCT_STATE** | Cada loop deja el producto en un estado distinto y verificable (feature integrada, DEFER con trigger, POC retirado, evidencia escrita). Loop sin cambio de estado = no cerrar. | Diff de estado entre inicio y fin del loop documentado. |
| 8 | **STABILIZATION_ONLY_FOR_DEMONSTRATED_DEFECT** | Los loops de estabilización/fixes solo se justifican con defecto demostrado (reproducción, dump, test rojo). Prohibido "estabilizar" por intuición. (Referencia: doble free `0xc0000374` aislado por dumps 3/3 [HECHO: worker_92].) | Defecto con evidencia de reproducción adjunta. |
| 9 | **EXTERNAL_POC_MUST_BE_REMOVABLE** | Todo POC externo vive en sandbox autocontenido y se retira verificando ausencia de rastros (paso 5/13, §3.2). | `git status` de BASE limpio tras retiro + venv intacto. |
| 10 | **INTEGRATION_BEHIND_STABLE_INTERFACE** | Toda tecnología entra por adapter detrás de las interfaces del catálogo; prohibido cablear directo a RTSP/SourceManager/pipeline. | Adapter referencia interfaz del catálogo; 0 imports directos de la dependencia en el Core. |
| 11 | **FULL_REGRESSION_BEFORE_BASE_COMMIT** | Nada se commitea a BASE sin regresión completa PASS y `NEW_DEPENDENCIES` declarado (paso 10→12). | Gate G3/G16 en el loop. |
| 12 | **TES_UPDATED_AT_EACH_CERTIFIED_CHECKPOINT** | TES (registry, DEC, capability matrix) se sincroniza en cada checkpoint certificado del flujo, no al final "cuando haya tiempo" (paso 13). | Diff TES del loop con fecha y ítems actualizados. |

**Fórmula anti-loop en una línea:** cada iteración debe terminar en una decisión escrita, un estado de producto distinto y evidencia verificable — de lo contrario, no es un loop de producto, es un bucle.

---

## 7. Referencias cruzadas

- **Extension Boundaries + ZERO-REWRITE POLICY:** documento `EXTENSION_BOUNDARIES.md` (entregado junto a este playbook en la ronda LOOP-0018S; catálogo de 8 backends: InferenceBackend, TrackingBackend, ActivityBackend, SegmentationBackend, ReIDBackend, EvidenceBackend, DiscoveryBackend, ReasoningBackend; regla de no mezcla con RTSP/SourceManager; política de 3 preguntas antes de desarrollar).
- **Radar:** `technology_radar.md` (34 tecnologías, 7/4/10/10/3, 0 PENDING).
- **Matriz de ingesta:** `external_experience_ingestion_matrix.md` (una decisión por tecnología).
- **Evidencia del loop:** `evidence/loop_0018s/` (este archivo + los otros 10 entregables).

— Fin de TECHNOLOGY_INGESTION_PLAYBOOK.md (v1.0, LOOP-0018S)
