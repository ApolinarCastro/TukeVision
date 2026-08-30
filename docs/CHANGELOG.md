# Registro de Cambios — TukeVision

Todos los cambios notables en este proyecto se documentan en este archivo.

---

## [3.0.0-strict-truth-enforced] - 2026-08-30

### Cierre Estricto de Verdad de Runtime (`TV-F12-STRICT-RUNTIME-TRUTH-ENFORCEMENT-06`)
- **Ejecución y Persistencia de Soak Continuo de 1800s:** Completada corrida ininterrumpida de 1800.89 segundos con muestreo periódico a `soak_samples.jsonl`, demostrando estabilidad de memoria (12.84 MB crecimiento, 0 fugas, 0 congelamientos de UI).
- **Medición Geométrica Real de Grid 6:** Instrumentado `get_grid_layout_snapshot()` en `TkApp`, registrando en `grid6_physical.json` y `grid6_tile_geometry.json` una cuadrícula física de 1260x593 con 6 celdas reales (0 solapes, 0 recortes, 2.3% espacio muerto).
- **Zero-Fake y Eliminación Absoluta de Fallbacks:** Reemplazados todos los valores supuestos o precalculados en modo certificación por evaluadores booleanos estrictos sobre datos observados (`test_strict_runtime_truth.py`).
- **Trazabilidad RTSP de Focus HD:** Documentada la conmutación a subtype 0 en `focus_rtsp_trace.json`, dejando constancia honesta del límite físico de conectividad con DVRs locales (`TV_F12_RUNTIME_TRUTH_CLOSED_WITH_EXTERNAL_LIMITATIONS`).
- **Regresión Automática Total:** **979 pruebas pasadas** (0 fallidas, 0 errores, 4 omitidas, 15 subtests pasados) en 95.75s.
