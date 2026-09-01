# EXTENSION_BOUNDARIES + ZERO-REWRITE POLICY

**Documento permanente de TukeVision** · **LOOP de creación:** 0018S (2026-08-16) · **Versión:** 1.0
**Fuente:** worker_94 ENTREGABLE 2 (ronda 2, verificado S4). Documentación del PATRÓN: **no se crea ninguna interfaz nueva en código con este documento**; las interfaces que ya existen se citan; las que no existen se definen como contrato de destino para futuros adapters.
**Credenciales redactadas. Canario de trazado RTSP: ausente.**

## 1. Principio: la tecnología externa entra por interfaces desacopladas, nunca por el cableado directo

El pipeline certificado (SPEC-0001) y la capa de captura RTSP (`RTSPSource`/`SourceManager`, E-01) son el núcleo sagrado. **Ninguna tecnología nueva se mezcla con RTSP/SourceManager** y ninguna dependencia externa se importa directamente en `src/app/pipeline.py`, `src/capture/` ni `src/ui/`. En su lugar, TukeVision define un catálogo de **backends** (interfaces de rol) que separan "qué hace el sistema" (contrato) de "quién lo implementa" (adapter). El Core depende del contrato; el adapter encapsula la tecnología y puede ser reemplazado, desactivado o retirado sin regresión.

Este patrón ya opera en el código real: `InferenceEngine` en `src/inference/engines.py` (Deterministic/Yolo) es el precedente certificado del patrón [HECHO: worker_90 §2.2, LOOP-0018Q]. El resto del catálogo extiende ese mismo principio.

## 2. Catálogo de interfaces (backends)

Convención del contrato mínimo: se lista propósito, contrato (métodos/entradas/salidas), qué existe YA en BASE que cumple el rol, y qué tecnologías del radar la usarían. Los contratos futuros se describen en el nivel de detalle necesario para gobernar adapters; su forma exacta se fija cuando el primer adapter se aprueba (paso 8 del playbook).

### 2.1 InferenceBackend

- **Propósito.** Ejecución de inferencia de visión (detección, clasificación, embedding) de forma selectiva, presupuestada y aislada por cámara. Es el rol de "qué ve el sistema".
- **Contrato mínimo.** Implementa el patrón de `InferenceEngine`: construir a partir de config; recibir un frame (o batch) + política (QUALITY/BALANCED/ECONOMY); devolver un resultado canónico (detecciones con clase/conf/box + `evidence_ref`) o un evento de inferencia trazable; fallar aislado sin tumbar la cámara.
- **Qué existe YA en BASE.** `src/inference/engines.py` (`DeterministicInferenceEngine`, `YoloInferenceEngine` — composición sobre `src/detection/person_detector.py`), `src/inference/contract.py`, `src/inference/selective.py` (`SelectiveInferencePipeline`, 42/42 tests), `src/inference/events.py` (`InferenceEvent`, `EventDetector`). [HECHO: worker_90 filas 11–14]
- **Tecnologías del radar que la usarían.** YOLO11n (ACTIVE, ya implementa el rol); instance segmentation (DEFER P3 — sería un `SegmentationBackend` que comparte el patrón); ReID embeddings (DEFER P3 — solo como encoder de apariencia, ver ReIDBackend).

### 2.2 TrackingBackend

- **Propósito.** Identidad TEMPORAL y LOCAL por cámara (ciclo de vida de tracks), sin correlación cross-cámara ni biometría (DEC-0036, DEC-0013, DEC-0019). Base para conteo deduplicado, trayectorias y actividades.
- **Contrato mínimo.** Consumir eventos/inferencias de una cámara; mantener estado de tracks (crear/actualizar/cerrar con timeout y retención acotada); emitir tracks/actividades temporales canónicas con timestamps UTC; aislado por cámara; prohibida la exportación de identidad cross-cámara.
- **Qué existe YA en BASE.** Dos implementaciones legítimas según la cadena: `src/tracking/person_tracker.py` (ByteTrack, cadena heredada 2.1, CERTIFIED) y `src/temporal/tracker.py` (`LocalTracker`, 33/33 tests, LOOP-0018R) + `src/temporal/contract.py` (`LocalTrack`, `TemporalActivity`). [HECHO: worker_90 filas 3, 15]
- **Tecnologías del radar que la usarían.** ByteTrack (ACTIVE); people flow E-02 (EXTENSION_CANDIDATE P1 — dedup por ventana temporal sobre tracks locales); trajectory analytics (EXTENSION_CANDIDATE P2); ReID (DEFER — el rol NO lo cubre: embeddings fuera por gobernanza).

### 2.3 ActivityBackend

- **Propósito.** Capa de observación/derivación de actividad a partir de trayectorias, zonas y tiempo (dwell, permanencia, presencia temporal). Explícitamente NO clasifica intención/robo/sospecha (DEC-0019).
- **Contrato mínimo.** Recibir observaciones/tracks por cámara; aplicar política de muestreo (ObservationPolicy); producir observaciones canónicas inmutables y actividades temporales genéricas (PERSON_PRESENCE/OBJECT_PRESENCE) en cola acotada.
- **Qué existe YA en BASE.** `src/observations/activity.py` (`ActivityLayer`, `BoundedObservationQueue`, `ObservationPolicy` QUALITY/BALANCED/ECONOMY — 39/39 tests) y `src/temporal/contract.py` (actividades temporales). ⚠️ Ninguna de las dos está cableada al pipeline de producto (H1 [HECHO: worker_90]). El rol existe como módulo certificado sintéticamente; cablearlo es prioridad del roadmap, no una ingesta de tecnología.
- **Tecnologías del radar que la usarían.** CNN/activity recognition (PATTERN_REUSE_ONLY hoy — la taxonomía se implementará como derivación determinista tras este rol, no como red); people flow (conteo por zona sobre observaciones); heatmaps (DEFER).

### 2.4 SegmentationBackend

- **Propósito.** Segmentación selectiva (persona/producto/entorno) cuando un gap aprobado lo justifique. Rol de extensión del InferenceBackend, no del núcleo.
- **Contrato mínimo.** Mismo patrón de construcción/selectividad/presupuesto que InferenceBackend; devolver máscaras por instancia (o por clase) además de boxes; respetar el presupuesto de cómputo (segmentación ≫ detección en CPU [HECHO: worker_92 fila 20]).
- **Qué existe YA en BASE.** NADA (NO_EXISTE; fila "segmentation selectiva" PRIO 7 sin gap aprobado [HECHO: worker_92 fila 20]).
- **Tecnologías del radar que la usarían.** Instance segmentation (DEFER P3 — nuevo modelo, rompería presupuesto CPU y lock; requiere decisión de producto).

### 2.5 ReIDBackend

- **Propósito.** Codificación de apariencia para deduplicación/correlación por persona. **Rol con gobernanza bloqueante hoy**: embeddings = datos biométricos → DEC-0013/0019/0036; la correlación cross-cámara de identidad está prohibida [HECHO: worker_92 fila 22]. El rol se documenta para que cualquier futura decisión humana tenga dónde aterrizar; su activación exige DEC explícita.
- **Contrato mínimo (diseño previo existente).** Encoder de apariencia pluggable (F1 histograma no biométrico, F2/F3 OSNet/onnxruntime), galería con TTL y matching por umbral; si algún día se aprueba, detrás de `src/identity/` y con muestreo por eventos (nunca por frame en el flujo principal).
- **Qué existe YA en BASE.** NADA en BASE (E-03 solo portable, EXPERIMENTAL; bloqueada). Diseño completo F1–F4 documentado (104–136 h) [HECHO: worker_92 fila 22].
- **Tecnologías del radar que la usarían.** ReID (OSNet/torchreid/deep_sort/histograma/YOLO-embed) — DEFER P3 con POC aislado condicionado a decisión humana; Faceplugin/Warden — REJECT (gobernanza). **Nota:** el gap del doble conteo se resuelve primero por la vía NO biométrica (people flow + ventanas temporales).

### 2.6 EvidenceBackend

- **Propósito.** Persistencia inmutable y consultable de la evidencia (frames + metadatos con hash) y propagación de referencias (`evidence_ref`) desde inferencia/tracking hasta almacenamiento.
- **Contrato mínimo.** Guardar evidencia inmutable por alerta/evento (frame + metadata.json + sha256); propagar y resolver `evidence_ref` (first/latest/best); opcionalmente índice consultable (SQLite stdlib) para búsqueda/reportes; fallo de escritura controlado (EvidenceExistsError).
- **Qué existe YA en BASE.** `src/evidence/store.py` + `models.py` (CERTIFIED, cadena heredada); `evidence_ref` en `src/inference/contract.py`/`events.py` y en `src/temporal/tracker.py` (G18/G19 PASS) — pero **no materializado en disco en runtime** (H3 [HECHO: worker_90]). El puente ref→disco es trabajo de cableado interno, no una ingesta.
- **Tecnologías del radar que la usarían.** SQLite índice de evidencia (EXTENSION_CANDIDATE P2, 0 deps); openpyxl/exportación (DEFER P3 — sobre el índice, rompe lock); backup/restore de SmartPSS (EXTENSION_CANDIDATE P1 — patrón de escritura atómica, no dependencia).

### 2.7 DiscoveryBackend

- **Propósito.** Descubrimiento de cámaras en la LAN (WS-Discovery/SSDP/ONVIF) para no teclear URLs; habilitaría también consulta de capacidades (PTZ, grabaciones).
- **Contrato mínimo.** Escanear/descubrir dispositivos; devolver descriptores de cámara (dirección, canales, subtipos, capacidades) que alimenten el catálogo de config; fallar limpio (sin bloquear el arranque) y sin credenciales en logs (política de redacción vigente).
- **Qué existe YA en BASE.** NADA (NO_EXISTE; URL tecleada por sesión). `build_rtsp_url`/`rtsp_url.py` es el consumidor natural de lo que discovery entregaría. [HECHO: worker_92 fila 11]
- **Tecnologías del radar que la usarían.** ONVIF WS-Discovery/SSDP (DEFER P3, POC condicionado); patrones de red SmartPSS P1-5 (EXTENSION_CANDIDATE — health polling y métricas, sin dependencia).

### 2.8 ReasoningBackend

- **Propósito.** "AI second opinion" opcional POST evento: razonamiento/explicación/priorización sobre evidencia determinista ya certificada. El sistema funciona sin él (AI_POLICY: determinista + razonamiento opcional + UNKNOWN válido [HECHO: worker_92 fila 26/27]).
- **Contrato mínimo.** Recibir evidencia determinista (evento + referencias); devolver opinión/priorización opcional no vinculante con trazabilidad; ausencia del backend = el flujo sigue intacto; UNKNOWN es resultado válido.
- **Qué existe YA en BASE.** NADA en código; especificación en `AI_POLICY.md` y ARCHITECTURE.md #14. Qwen fue REJECTED (DEC-0023: API/red/licencia contradicen política local y portabilidad) [HECHO: worker_92 fila 26].
- **Tecnologías del radar que la usarían.** Qwen-MM-Plugins (REJECT); cualquier proveedor local conforme que algún día se apruebe (entraría por este rol). CactusCompute Hybrid (PATTERN_REUSE_ONLY — valida la separación edge/razonamiento, no se integra).

## 3. Regla de no mezcla con RTSP/SourceManager

- El catálogo de backends es el **único** punto de entrada de tecnología al núcleo. RTSP/SourceManager (`src/capture/`) queda fuera de ese catálogo a propósito: la captura es el componente con mayor riesgo nativo (double free `0xc0000374` en el wrapper FFmpeg de OpenCV durante reconexión, SIN RESOLVER [HECHO: worker_92]) y con certificación física vigente (MULTICAMERA4_PHYSICAL_CERTIFIED [HECHO: worker_90]).
- Consecuencias operativas:
  1. Ninguna librería de video/red/decode se instala "para mejorar la captura" sin pasar el playbook completo y sin cerrar/aislar el riesgo nativo (el fix forense del call-site es prerrequisito documentado de los cambios de reconexión [HECHO: worker_92 fila 1/33]).
  2. Los cambios permitidos en captura son ADITIVOS dentro de las interfaces existentes (`RTSPSource._reconnect`, config `rtsp`) con tests deterministas, como los patrones de red RTSP P1 (transporte explícito, backoff+jitter, no-retry-401) — nunca reemplazos del componente certificado.
  3. Un adapter de tecnología nueva que necesite frames usa la cola/snapshot que SourceManager ya entrega; no inyecta código en el hilo de captura.

## 4. ZERO-REWRITE POLICY (Fase 9 del flujo S)

Toda recomendación tecnológica — de este documento, del radar o futura — debe responder, en orden, tres preguntas antes de proponer desarrollo:

1. **¿Podemos reutilizar algo de BASE / portable / TES?** (módulo certificado, extensión portable clasificada REUSABLE_WITH_ADAPTATION, diseño/spec ya escrita, patrón ya extraído). Si SÍ → se reutiliza/adapta; se documenta `WHAT_WE_CAN_REUSE`.
2. **¿Existe una extensión mature (librería/estándar/patrón verificado) que resuelva el gap?** Si SÍ → adapter detrás de la interfaz del catálogo (§2), antes que desarrollo custom.
3. **Solo entonces, ¿desarrollar?** → se marca `CUSTOM_DEVELOPMENT_REQUIRED` **con evidencia escrita de que (1) y (2) no resuelven el gap** (Paso 3 del playbook).

**Regla de oro:** reescribir o re-desarrollar algo que ya existe certificado (en BASE) o estudiado (en TES/portable) es un anti-patrón prohibido — la excepción única es la regla 4 del ANTI-LOOP (reescritura de componentes certificados solo con regresión completa que la avale).

**CUSTOM_DEVELOPMENT_REQUIRED — evidencia mínima exigida:**
- (1) Verificación de reuso: búsqueda en BASE (`src/` + tests) y en portable (extensiones E-*) con resultado "no cubre" o "cubre parcialmente, adaptación X".
- (2) Verificación de extensión mature: búsqueda de solución externa con resultado "no existe madura / no compatible (stack, licencia, gobernanza)".
- Conclusión escrita: "el gap G solo se cierra con desarrollo propio porque…" + estimación de esfuerzo + impacto en presupuesto de cómputo y lock.
- Sin esta evidencia, la petición se devuelve a DEFER. [Patrón aplicado en el radar: personas-vs-maniquíes y people flow = custom/adaptación con evidencia; instance segmentation = DEFER sin gap aprobado; ReID = DEFER por gobernanza pese a tener diseño completo. HECHO: worker_92]

## 5. Mapa resumen: rol ↔ implementación BASE ↔ tecnologías del radar

| Interfaz (rol) | Ya existe en BASE (rol cumplido) | Pendiente de implementación | Tecnologías del radar que la usarían |
|---|---|---|---|
| InferenceBackend | `src/inference/engines.py` (Deterministic/Yolo), `contract.py`, `selective.py` (42/42) [HECHO] | Cableado al pipeline de producto (H1) | YOLO11n (ACTIVE); segmentation (DEFER); ReID-embed (DEFER) |
| TrackingBackend | `src/tracking/person_tracker.py` (ByteTrack, CERTIFIED) + `src/temporal/tracker.py` (33/33) [HECHO] | Cableado (H1); dedup por ventana temporal | ByteTrack (ACTIVE); people flow (P1); trajectory (P2) |
| ActivityBackend | `src/observations/activity.py` (39/39) + `src/temporal/contract.py` [HECHO] | Cableado (H1); derivaciones deterministas de la taxonomía | CNN/activity (PATTERN_REUSE_ONLY); heatmaps (DEFER) |
| SegmentationBackend | NADA (NO_EXISTE) | Todo (si se aprueba gap) | Instance segmentation (DEFER P3) |
| ReIDBackend | NADA en BASE (E-03 portable, bloqueada por DEC) [HECHO] | Todo (solo tras DEC explícita; F1 no biométrico primero) | ReID (DEFER P3); Faceplugin (REJECT) |
| EvidenceBackend | `src/evidence/store.py` (CERTIFIED) + `evidence_ref` (G18/G19 PASS) [HECHO] | Materializar ref→disco (H3); índice SQLite | SQLite índice (P2); openpyxl (DEFER); backup (P1) |
| DiscoveryBackend | NADA (NO_EXISTE) | Todo (si se aprueba) | ONVIF (DEFER P3, POC condicionado) |
| ReasoningBackend | NADA en código (AI_POLICY como spec) [HECHO] | Todo (opcional; flujo funciona sin él) | Qwen (REJECT); proveedor local futuro; CactusCompute (patrón) |

## 6. Cierre del entregable

- Este documento NO crea interfaces en código: es el catálogo de destino que gobierna futuros adapters (paso 8 del playbook). La única interfaz materializada hoy es la que ya existe (`InferenceEngine` y sus contratos).
- **Zero-rewrite se audita en cada loop (G11/G17)**: ningún worker del flujo S puede proponer "rehacer" un módulo certificado; toda propuesta entra por el catálogo o se rechaza con la evidencia de §4.
- Regla transversal: `PORTABLE_IS_NOT_PRODUCT` (ANTI-LOOP 6) — las extensiones E-02…E-05 migran a BASE solo vía playbook, clasificadas por su applicability matrix (REUSABLE_WITH_ADAPTATION ×3, REQUIRES_DECISION ×1 [HECHO: worker_92 fila 34]).

— Fin de EXTENSION_BOUNDARIES.md (v1.0, LOOP-0018S)
