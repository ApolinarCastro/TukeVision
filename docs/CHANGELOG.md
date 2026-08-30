# Registro de Cambios — TukeVision

Todos los cambios notables en este proyecto se documentan en este archivo.

---

## [3.0.0-final-truth-physical-tes] - 2026-08-30

### Corregido (Cierre Quirúrgico Zero-Fake Absoluto y Salud Factual)
- **Eliminación Total de Event → Situation (`src/ui/tk_operational_panels.py`):** Suprimido cualquier camino de conversión de eventos, detecciones o cadenas de alerta a situaciones. Solo se procesan `SituationRecord` o `SituationViewItem` legítimos con `situation_id` y `situation_type` definidos por el backend.
- **Prohibición de IDs y Tipos Sintéticos:** Eliminada la creación de IDs arbitrarios (`SIT-...`, `EVT-...`) y tipos por defecto (`ALERTA`, `DETECCIÓN`) desde la UI.
- **Severidad y Estado Epistémico No Deducidos:** La severidad y el estado epistémico no se deducen a partir de umbrales de confianza en la interfaz; se consumen del backend o reportan como `UNKNOWN`.
- **Diagnóstico de Salud Global Factual:** Eliminada la inferencia de salud basada en la mera cantidad de streams activos (`SALUDABLE if live_count > 0`). Si no existe un reporte agregado de salud, se indica formalmente `NO DETERMINADO`.

### Gobernanza y Trazabilidad TES V3
- **Creación de Estructura Canónica `TES/`:** Creados `TES/README.md`, `TES/PLAN_MAESTRO_V3.md`, `TES/CAPABILITY_MATRIX.md`, `TES/DECISION_LOG.md` y `TES/TECHNOLOGY_RADAR.md`.
- **Regla Permanente de Cierre:** Implementada la regla `NO MATERIAL CHANGE IS COMPLETE UNTIL: CODE + TEST + DOCS + TES RECONCILIATION ARE CONSISTENT`.
- **Evidencia Física Completa:** Generado paquete de evidencia en `evidence/TV-F12-SURGICAL-FINAL-TRUTH-PHYSICAL-TES-03/` con 14 artefactos estructurados y capturas reales.
- **Suite de Regresión Pytest:** Verificada la suite completa con 100% de éxito (950 pruebas pasadas).
