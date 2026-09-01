# NEXT_PRODUCT_ADVANCE_PRIORITIES — LOOP-0018S

**LOOP:** 0018S (Fase 8) · **Fecha:** 2026-08-16 · **Modo:** SOLO LECTURA del producto (priorización; sin implementar)
**BASE:** `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision` · **HEAD:** `cfad931` (loop-0018r, 16-08 18:55)
**Fuente:** worker_95 (ronda 2). **Regla:** máximo 5 prioridades. Credenciales redactadas. Canario de trazado RTSP: ausente.

---

## 0. Estado real certificado que condiciona la priorización (resumen)

1. **[HECHO]** Regresión BASE 359/359 PASS (unittest, intérprete del venv portable), compileall PASS, SECRET_LEAK=0 (worker_91).
2. **[HECHO]** H1 CRÍTICO: la cadena PRODUCT ADVANCE (SourceManager → ActivityLayer/ObservationPolicy → SelectiveInferencePipeline → LocalTracker) está implementada y certificada sintéticamente (39/39 + 42/42 + 33/33 + demo real 0018q), pero **ningún entry point de producto importa `src.inference`, `src.temporal` ni `src.observations.activity`** (grep verificado). El producto que se ejecuta sigue siendo la cadena 2.1 monofuente heredada.
3. **[HECHO]** H2: `dist/` OUTDATED — build 15-08 19:32, MANIFEST git_head `4e530f3` (11-08), **pre-E01 y pre-advance**.
4. **[HECHO]** H3: `evidence_ref` del avance existe solo en memoria; el único almacenamiento físico de runtime sigue siendo el EvidenceStore del flujo viejo.
5. **[HECHO]** H4: el `.venv` del BASE está roto (redirector → ruta inexistente de otro usuario, exit 103); pytest ausente en todos los entornos; la regresión se ejecuta con el venv portable.
6. **[HECHO]** H5: zones/dwell/risk/alerts/evidence son CERTIFIED en el flujo monofuente viejo; **no existen para el flujo multicámara** (per-camera pipeline = PARTIAL, capacidad 44).
7. **[HECHO]** Radar: P1 concretos = personas-vs-maniquíes (24–34 h, 0 deps), people flow deduplicado (E-02 + ventana temporal, no biométrico), robustez RTSP (transporte TCP/backoff+jitter/no-retry-401/auto-switch). Doble free nativo `0xc0000374` SIN RESOLVER (call-site pendiente).
8. **[HECHO]** Portable (worker_93): MIGRATE = `retail/trajectory.py` (E-02), `capture/quality_engine.py` (E-05), `src/identity/` (E-03, BLOQUEADO por gobernanza), Command Center UI (tk_view 43 KB), 5 scripts de test únicos. El resto ya está en BASE (12 módulos byte-idénticos).

**Consecuencia de priorización (regla del usuario, con evidencia contraria aplicada):** la preferencia funcional 1 (continuidad temporal/local) y 2 (evidencia operacional) ya están implementadas y certificadas sintéticamente; el primer paso lógico es **INTEGRAR lo certificado**, no implementar más módulos aislados. La Fase 11 ordena que, con dist OUTDATED, la generación del ejecutable oficial sea el **P0 siguiente**. El venv BASE roto es prerrequisito de higiene.

---

## 1. PRIORIDADES (P0..P4, máximo 5)

### P0 — Ejecutable oficial regenerado desde HEAD + entorno BASE saneado (cimientos de entrega)

- **Objetivo:** (a) regenerar el venv BASE desde `requirements.lock.txt` para que la regresión 359/359 corra con el intérprete oficial; (b) reconstruir `dist/TukeVision/` + zip desde HEAD `cfad931` con `MANIFEST.json` correcto (git_head real, fecha, sha256 del modelo) incluyendo `src/inference/`, `src/temporal/`, `src/observations/activity.py`, `src/capture/source_manager.py`, `config/default.json` completo, y excluyendo instrumentación y el backup `live_sources.BASE_preE01.bak.py`.
- **Justificación:** **[HECHO]** H2 (dist actual entrega código del 11-08 pre-E01/pre-advance; MANIFEST miente); **[HECHO]** H4 (venv BASE roto impide el comando de regresión literal). La Fase 11 ordena el ejecutable oficial como P0 siguiente ante OUTDATED.
- **Qué reutiliza:** `install/package.ps1`, `requirements.lock.txt`, `MANIFEST.json` como plantilla, procedimiento de secret scan de worker_91.
- **Trabajo estimado:** **[INFERENCIA]** ~2–4 h (venv 1–2 h; rebuild 1–2 h). Esfuerzo S.
- **Dependencias:** ninguna técnica bloqueante. **Desbloquea P1, P2, P4.**
- **Criterio de certificación:** regresión 359/359 con el **venv BASE**; compileall PASS; secret scan post-build = 0; `MANIFEST.json` con git_head = HEAD real y sha256 del modelo; smoke test (fuente FILE); zip con hashes SHA-256 registrados.

### P1 — Integración de la cadena 2.2 al producto (cableado SourceManager→ActivityLayer→SelectiveInference→LocalTracker + evidencia operacional)

- **Objetivo:** que el producto que se ejecuta consuma la cadena certificada: frames de SourceManager (multicámara) → ActivityLayer con ObservationPolicy → SelectiveInferencePipeline → EventDetector → LocalTracker (track_id local, TemporalActivity PERSON_PRESENCE) → eventos/alertas del flujo heredado → **persistencia de `evidence_ref` en disco** (first/latest/best resolubles a archivo con sha256). Mantener la cadena 2.1 heredada como modo de compatibilidad configurable.
- **Justificación:** **[HECHO]** H1 (capas implementadas y certificadas sintéticamente pero NO cableadas); **[HECHO]** H3 y capacidad 44 (sin cableado no existe pipeline por cámara en runtime ni evidencia física del avance). Entrega las preferencias funcionales 1 y 2 del usuario en el producto real. Mayor multiplicador de impacto: desbloquea P2 y correlaciones futuras.
- **Qué reutiliza:** todo el stack 0018p/q/r, SourceManager 0018o (física 4-cam), EvidenceStore, config/default.json, tests de equivalencia, patrón de aislamiento por cámara.
- **Trabajo estimado:** **[INFERENCIA]** 16–32 h (2–4 días). Esfuerzo M–L.
- **Dependencias:** **requiere P0**. **Desbloquea P2.**
- **Criterio de certificación:** (1) tests de integración nuevos (`test_pipeline_advance.py`): feed multicámara sintético produce observaciones → inferencia selectiva con saltos por política → eventos → LocalTracks → TemporalActivities; (2) **evidencia física**: `evidence_ref` resuelve a archivo en disco con sha256 (cierre de H3); (3) regresión 359/359 + nuevos verdes en venv BASE; (4) invariante de aislamiento por cámara; (5) STREAM_LOST sigue mapeado; (6) UI sigue mostrando frames. Criterio adicional: **rebuild de dist desde el nuevo HEAD**.

### P2 — People flow deduplicado (conteo IN/OUT/INSIDE por zona con ventana temporal, no biométrico)

- **Objetivo:** migrar `retail/trajectory.py` (E-02, portable) al BASE adaptado a multicámara y cablear contadores IN/OUT/INSIDE por zona sobre los LocalTracks del producto, con deduplicación por ventana temporal de re-entrada (≥30 s) — **sin identidad ni biometría** (DEC-0013/0036). Corrige el síntoma reportado por el usuario: misma persona contada N veces.
- **Justificación:** **[HECHO]** radar: doble conteo confirmado (worker_30, causa raíz: FlowCounter indexado por track_id efímero); worker_93 marca `retail/trajectory.py` como MIGRATE. **[HECHO]** capacidad 19 = EXPERIMENTAL_PORTABLE_ONLY. Entrega la preferencia funcional 3.
- **Qué reutiliza:** E-02, `src/temporal/tracker.py`, `src/context/zone.py`; ajustar poda de trayectorias (300 pts ≈20 s insuficiente para ventanas ≥30 s).
- **Trabajo estimado:** **[INFERENCIA]** 8–16 h. Esfuerzo M.
- **Dependencias:** **requiere P1**.
- **Criterio de certificación:** (1) tests deterministas: misma trayectoria re-entrando dentro de la ventana → 1 conteo; dos trayectorias → 2 conteos; (2) validación física con grabación 4-cam y ground truth manual; (3) verificación de no-biometría; (4) regresión completa verde.

### P3 — Filtro personas-vs-maniquíes (HumanVerifier, filtro de estaticidad por track)

- **Objetivo:** implementar el diseño completo del cluster mannequin (worker_60/61/62): máquina de estados UNKNOWN→MOVING/STATIC_SUSPECT/STATIC_CLEARED post-tracking, pre-conteo/zona; `static_from_birth` + dwell ≥90 s + probation; regla "si alguna vez se movió, jamás es maniquí"; modo tag para calibración física.
- **Justificación:** **[HECHO]** radar: YOLO clase COCO 0 no distingue maniquíes; un maniquí dispara PERMANENCIA_PROLONGADA falsa (dwell→∞) — impacto directo en el piloto retail Nicopoly; diseño completo (24–34 h, 0 deps, <1–5 ms/frame).
- **Qué reutiliza:** diseño del cluster mannequin, `_stay_seconds` (dwell), `person_tracker.py` o `src/temporal/tracker.py` (P1) como fuente de tracks, config para umbrales.
- **Trabajo estimado:** **[HECHO]** 24–34 h (A 10–14 h / B 6–8 h / C 8–12 h). Esfuerzo M.
- **Dependencias:** 0 deps (paralelo a P1 en modo sintético); **certificación de producto multicámara requiere P1**.
- **Criterio de certificación:** (1) tests de la máquina de estados; (2) validación física: maniquí >90 s NO genera PERMANENCIA_PROLONGADA ni cuenta IN; persona sentada con historial de movimiento SÍ; (3) regresión completa verde.

### P4 — Robustez de la fuente RTSP (transporte TCP explícito, backoff+jitter, no-retry-401, auto-switch subtype)

- **Objetivo:** en `RTSPSource` (aditivo, sin romper E01): transporte TCP explícito + fallback UDP vía `OPENCV_FFMPEG_CAPTURE_OPTIONS`/config; backoff con jitter y clasificación de error; **no reintentar tras 401**; auto-switch main↔sub reutilizando `quality_engine.py` (E-05, MIGRATE); búfer FFmpeg acotado. Compuerta forense: cualquier cambio en reconexión se certifica contra el patrón determinista LOOP-0018B y, si se reproduce, con dump completo + PageHeap para cerrar el call-site del double free.
- **Justificación:** **[HECHO]** radar: reconexión a delay fijo (2 s ×3) sin clasificación de error; transporte implícito; sin auto-switch; **[HECHO]** doble free `0xc0000374` SIN RESOLVER. La captura 4-cam física está CERTIFICADA (0018o), pero es hardening operativo, no funcionalidad nueva.
- **Qué reutiliza:** `live_sources.py` E01 (reader thread, watchdog, contabilidad E1–E4, 87/87), `rtsp_url.py`, patrones worker_80, `quality_engine.py` (MIGRATE), tooling forense + dumps de LOOP-0018H/I.
- **Trabajo estimado:** **[HECHO]** transporte/backoff/no-retry-401 ≈0.5 d c/u; auto-switch ≈1–1.5 d → **[INFERENCIA]** 16–24 h + tiempo de compuerta forense variable. Esfuerzo M.
- **Dependencias:** P0 (regresión 87/87 + 359/359). Independiente de P1–P3 (paralelo).
- **Criterio de certificación:** (1) tests deterministas de backoff/jitter, no-retry-401, transporte TCP explícito; (2) validación física: kill/restart de una cámara durante un run 4-cam → reconexión con backoff y 0 doble-free (o crash documentado con dump); (3) auto-switch main↔sub verificado; (4) regresión 87/87 + 359/359 verde.

---

## 2. Orden y dependencias (cadena)

```
P0 (cimientos: venv BASE + dist desde HEAD) ──► desbloquea certificación de TODO
        │
        ▼
P1 (integración cadena 2.2 al producto + evidencia operacional) ◄── preferencias 1 y 2 del usuario
        │                                          ▲
        ▼                                          │ paralelo (0 deps, sintético)
P2 (people flow deduplicado E-02 + ventana) ─┐     │
        │                                    │     │
        ▼                                    │     ▼
(preferencia 4: correlación temporal/topológica  P3 (HumanVerifier maniquíes)   P4 (robustez RTSP + compuerta forense)
 cross-cámara sin identidad — DIFERIDA a un      │                             (independiente, paralelo)
 siguiente LOOP, requiere P2 + DEC)              ▼
                                    certificación de producto multicámara de P3 requiere P1
```

**Por qué este orden:** P0 primero (Fase 11 + higiene: ejecutable oficial + venv sano). P1 segundo (máximo impacto: convertir código certificado-muerto en producto, cerrar H3, capacidad 44 → CERTIFIED). P2 tercero (síntoma del usuario + depende de P1). P3 en paralelo (0 deps, alto valor retail, certificación física espera P1). P4 al final (hardening de capacidad ya CERTIFIED, con compuerta forense).

## 3. Qué NO incluir (rechazados o diferidos, con motivo)

- **ReID / identidad de contexto (E-03) y Face Recognition:** REJECTED por gobernanza (DEC-0013/0019/0036; ley 19.628 Chile). El síntoma (doble conteo) se mitiga sin biometría con P2. No se incluye ni siquiera F1 no biométrico sin DEC humana explícita.
- **VLM / "segunda opinión IA" / "God Eye":** Qwen-MM REJECTED (DEC-0023); el gap queda como spec (AI_POLICY) sin proveedor.
- **Correlación cross-cámara de identidad:** prohibida por DEC-0036. La preferencia funcional 4 (correlación temporal/topológica sin identidad) se **difiere**: requiere P1 + P2 + DEC que acote el alcance.
- **Segmentation y detección de productos:** DEFER (P3) sin gap aprobado; UC-007 no aprobado; coste CPU alto.
- **ONVIF / PTZ / discovery:** DEFER (P3) sin caso de negocio; rompe lock; soporte de vendedor sin confirmar.
- **Web/API, playback, heatmaps, reportes xlsx, infraestructura externa:** DEFER/REJECT con trigger no cumplido.
- **UI Command Center portable (E-04) como prioridad propia:** se difiere a un siguiente LOOP (cambio de UI grande; su valor se multiplica mostrando datos de P1/P2).
- **`src/identity/` del portable (MIGRATE según worker_93):** excluido de P2/P3 por bloqueo de gobernanza; la migración de código no autoriza la activación de identidad.
- **Trajectory analytics standalone:** absorbido dentro de P2 (comparte módulo E-02).

**Nota de higiene transversal:** antes de cualquier MIGRATE desde portable (P2, P4), aplicar la limpieza de credenciales de `portable_exit_matrix.md` §1.3 (redactar IP del DVR e IPs LAN; no propagar canarios de prueba).

## 4. Trazabilidad

- **[HECHO]** Estados de capacidades, H1–H7, cadenas 2.1/2.2: worker_90 §1–4.
- **[HECHO]** 359/359 PASS, venv BASE roto, secret scan 0: worker_91.
- **[HECHO]** Decisiones P0–P3 por tecnología, doble free sin resolver, maniquí 24–34 h, E-02/ventana, robustez RTSP: worker_92.
- **[HECHO]** dist OUTDATED, MIGRATE/DISCARD/ARCHIVE, credenciales portable: worker_93.
- **[INFERENCIA]** Estimaciones de esfuerzo de P0, P1 y P2: señaladas como tales.
- Canario de trazado RTSP: verificado ausente de este documento.

— Fin de next_product_advance_priorities.md (LOOP-0018S)
