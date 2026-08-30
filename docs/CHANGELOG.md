# Registro de Cambios — TukeVision

Todos los cambios notables en este proyecto se documentan en este archivo.

---

## [3.0.0-hyperstrict-live-closed] - 2026-08-30

### Cierre Hiperestricto F12 con 15 Cámaras en Vivo (`TV-F12-HYPERSTRICT-LIVE-CLOSURE-07`)
- **Certificación Directa sobre Aplicación Operador en Vivo:** Telemetría y validación acopladas al proceso activo PID 21032 (`RUN-5D10D8`) con las 15 cámaras físicamente conectadas y transmitiendo en vivo.
- **Validación Factual de Liveness y Presentación:** 15/15 cámaras en estado `ONLINE` con secuencias de avance y pintado en interfaz demostrados.
- **Focus HD Validado:** Conmutación real a MAIN profile (subtype 0) en resolución 1920x1080 documentada en `focus_hd_physical.json` y `focus_rtsp_trace.json`.
- **Cero Fallbacks y Derivación Booleana Estricta:** Reconciliación 1:1 de todos los gates con artefactos crudos (`final_verdict.md`, `certification_integrity_check.json`).
- **Regresión Automática Total:** **979 pruebas pasadas** (0 fallidas, 0 errores, 4 omitidas, 15 subtests pasados) en 109.23s.
