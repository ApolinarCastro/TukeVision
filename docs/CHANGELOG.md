# Registro de Cambios — TukeVision

Todos los cambios notables en este proyecto se documentan en este archivo.

---

## [3.0.0-megaloop-truth-closed] - 2026-08-30

### Cierre Físico y Unificación de Runtime (`TV-F12-MEGALOOP-RUNTIME-TRUTH-CLOSURE-05`)
- **Unificación de Runtime en Mismo Proceso:** Implementado `RuntimeEvidenceCollector` y `RuntimeContext` que se adjuntan directamente a la instancia activa de `MulticameraRuntime` y `TkApp`, eliminando cualquier proceso o `SourceManager` paralelo.
- **Instrumentación de Secuencia Presentada:** Agregado `presented_frame_sequence` en `TkApp._render_panel` para correlacionar la entrega de video con el ciclo de refresco de Tkinter.
- **Conmutación Real de Flujo Focus HD (Subtype 0):** Corregido `MulticameraRuntime.set_focus` para ejecutar `switch_stream(cid, subtype=0, max_width=0)` y actualizar el HUD honestamente (`PERFIL: PRINCIPAL` y `(HD)` condicionado a $\ge 1280 \times 720$).
- **Simplificación UX de Estados Vacíos:** Reemplazados los contenedores vacíos gigantes de 1400px por tarjetas compactas centradas de 380px para `SITUACIONES` e `INVESTIGACIONES`.
- **Evaluador Booleano de Certificación:** Creado `CertificationEvaluator` que deriva todos los estados PASS/FAIL a partir de expresiones lógicas sobre datos observados.
- **Reconciliación TES V3 & Radar Tecnológico:** Actualizados `TES/TECHNOLOGY_RADAR.md`, `TES/CAPABILITY_MATRIX.md` y `TES/PLAN_MAESTRO_V3.md` integrando las directivas P0-65 y P0-66.
- **Regresión Automática Total:** 963 pruebas pasadas (0 fallos, 0 errores, 4 omitidas, 15 subtests pasados).
