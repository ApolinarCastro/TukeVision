# CLASIFICACIÓN DE ARCHIVO PORTABLE (OC-04)

**Fecha:** 2026-08-19
**Origen:** `archive/legacy/portable_migrate_0018u`
**Baseline:** `61d7ab38516d9da656a53c71d919f9857eda50d4`

---

## Resumen

Auditoría completa del paquete portable preservado en `LOOP-0018U` (13 ítems MIGRATE → PRESERVED_IN_LEGACY). Clasificación según criterios MACRO-OC-01:

| Categoría | Criterio |
|-----------|----------|
| **REUSE** | Patrones visuales probados, diseño system, helpers de presentación |
| **ADAPT** | Lógica de negocio que requiere integración con contratos AG-02/AG-03 |
| **KEEP_CURRENT** | Componentes ya certificados en BASE (SourceManager, EvidenceStore, Pipeline) |
| **REJECT** | Biometría/ReID (gobernanza), diagnóstico RTSP con credenciales, retail trajectory |

---

## Clasificación por Ítem

| # | Ítem Portable | Clasificación | Justificación |
|---|---------------|---------------|---------------|
| 1 | `src/identity/` (ReID F1) | **REJECT** | Biometría/ReID prohibida por DEC-0013/19/36. Governance: PRESERVED_DISABLED |
| 2 | `src/retail/trajectory.py` | **REJECT** | Supersedido por `LocalTracker` + `CrossCameraCorrelation` certificados (DEC-0040) |
| 3 | `src/capture/quality_engine.py` | **ADAPT** | Métricas de calidad útiles; integrar en `SystemHealthSampler` como extensibilidad |
| 4 | `src/ui/tk_view.py` (Command Center) | **REUSE** | **Patrones visuales principales recuperados**: `fit_display_size`, `bgr_frame_to_rgb`, `build_display_image`, design system (COLORS, FONT_*), Canvas dinámico, overlays, health bar. Ya integrados en BASE `tk_view.py` |
| 5 | `src/ui/controller.py` | **KEEP_CURRENT** | BASE ya tiene `UiController` certificado con pipeline single-source; portable usa arquitectura similar pero single-camera |
| 6 | `src/ui/state.py` | **KEEP_CURRENT** | BASE tiene `UiState` certificado; portable versión compatible |
| 7 | `src/app/pipeline.py` | **KEEP_CURRENT** | BASE tiene `Pipeline` + `OperationalPipeline` + `AdvanceChain` certificados (LOOP-0018Y) |
| 12 | `scripts/test_command_center_ui.py` | **REUSE** | Tests visuales válidos; adaptar a nueva API config-driven |
| 13 | `scripts/test_reconnect_accounting.py` | **REUSE** | Lógica de reconexión ya en `SourceManager` certificado (E-01) |
| 14 | `scripts/test_rtsp_liveness.py` | **REUSE** | Validación de liveness ya cubierta por tests certificados |
| 15 | `scripts/test_stderr_suppression.py` | **REUSE** | Patrón de supresión stderr ya en BASE |
| 16 | `scripts/test_ui_visual.py` | **REUSE** | Tests visuales válidos; adaptar a nueva API |
| 17 | `scripts/diagnose_rtsp_channels.py` | **REJECT** | Contiene credenciales/IPs de DVR reales; requiere redacción antes de uso externo (LEGACY_MANIFEST.md ⚠️) |

---

## Patrones REUSE ya Integrados en BASE

Los siguientes patrones del portable Command Center **ya están operativos** en `src/ui/tk_view.py`:

1. **fit_display_size** - Letterbox preservando aspect ratio, sin upscale fake
2. **bgr_frame_to_rgb** - Único punto de conversión de color
3. **build_display_image** - Escala LANCZOS solo presentación
4. **Canvas dinámico** - Paneles sobre Canvas que llenan espacio disponible
4. **Design System** - COLORS (dark navy, semantic green/amber/red), FONT_* (Segoe UI)
5. **Overlays legibles** - Info técnica en panel lateral, no tapa escena
6. **Health bar** - CPU/RAM/Disk + estado global + badges por cámara

---

## Patrones ADAPT Pendientes (MACRO-OC-01)

| Patín Portable | Objetivo MACRO-OC-01 | Estado |
|----------------|----------------------|--------|
| Grid 4x4 fijo (16 tiles) | OC-05: Grid dinámico 1/4/6/9/16 → N | ✅ Implementado via `grid_layout.py` + `grid_cells()` |
| Selector canal 1-16 | OC-06: Selector tienda + cámara/zona | ✅ Implementado en `tk_view.py` header |
| Doble clic → Fullscreen | OC-06: Doble clic → GRID_1 focus toggle | ✅ Implementado |
| Zoom rueda ratón | OC-07: Digital zoom | ✅ Implementado (`build_zoomed_display_image`) |
| PTZ botones direccionales | OC-07: PTZ gateado por `ptz_capability` | ✅ Implementado (UI + `Controller.ptz_capability`) |
| Flow metrics (IN/OUT/INSIDE) | OC-03/OC-11: Retail intelligence | 🔄 Parcial (trajectory.py rechazado, usar `CrossCameraCorrelation`) |

---

## Decisiones de Gobernanza Aplicadas

- **DEC-0013/19/36**: Biometría/ReID → REJECT (PRESERVED_DISABLED)
- **DEC-0040**: Correlación multicámara topológica (sin ReID) → KEEP_CURRENT (`CrossCameraCorrelation`)
- **SDL-03**: Geometría → Supervision solo si gap demostrado; portable usa rectángulos simples → ADAPT
- **SECRET_LEAK=0**: `diagnose_rtsp_channels.py` contiene credenciales → REJECT (requiere redacción)

---

## Conclusión

**13/13 ítems clasificados.** El portable no es la única copia (LEGACY_MANIFEST.md: 16/16 SHA-256 MATCH). Patrones visuales REUSE ya operativos en BASE. Componentes de gobernanza REJECT mantenidos en legacy. Componentes supersedidos (trajectory) reemplazados por core certificado.