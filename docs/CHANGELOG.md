# Registro de Cambios — TukeVision

Todos los cambios notables en este proyecto se documentan en este archivo.

---

## [3.0.0-physical-runtime-recertified] - 2026-08-30

### Recertificación Física y Gobernanza TES V3 (`TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04`)
- **Eliminación de Generador de Evidencia Sintética:** Eliminado `scripts/generate_tv_f12_final_truth_physical_tes_03_evidence.py` e invalidado el paquete anterior (`CERTIFICATION_INVALIDATED / CAUSE=SYNTHETIC_GENERATED_RUNTIME_EVIDENCE`).
- **Implementación de Telemetría Directa de Runtime:** Creado `scripts/capture_physical_runtime_evidence.py` que captura métricas en vivo desde `SourceManager`, `TkApp`, `ResourceTelemetry`, `psutil` y capturas directas de ventana con `PIL.ImageGrab`.
- **Registro de Incidente INC-001:** Documentado en `TES/DECISION_LOG.md` con la regla permanente: `A SCRIPT THAT GENERATES EXPECTED VALUES CANNOT CERTIFY PHYSICAL RUNTIME`.
- **Recertificación Completa en TES:** Actualizados `TES/PLAN_MAESTRO_V3.md` y `TES/CAPABILITY_MATRIX.md` vinculando las 13 capacidades a la telemetría viva de `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/`.
- **Regresión Automática Total:** Ejecución verificada con 955 pruebas pasadas (0 fallos, 0 errores, 4 omitidas, 15 subtests pasados).
