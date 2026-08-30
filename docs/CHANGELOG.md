# REGISTRO DE CAMBIOS DE TUKEVISION (CHANGELOG)

Todos los cambios notables de esta versión están documentados aquí.

---

## [3.0.0-phase12-production] - 2026-08-30

### Productización y Consolidación de Producción (`TV-F12-PRODUCTION-PRODUCTIZATION-01`)

#### Agregado
- **Módulo de Localización Centralizado (`src/localization/i18n.py`):**
  - Soporte completo para español (`es-CL`) por defecto.
  - Traducción exhaustiva de pestañas de navegación (`RESUMEN`, `EN VIVO`, `SITUACIONES`, `INVESTIGACIONES`, `EVIDENCIA`, `MAPA / ZONAS`, `ESTADO DEL SISTEMA`), controles, HUD y mensajes de alerta.
- **Sistema de Diseño Unificado (`src/ui/design_tokens.py`):**
  - Paleta de colores enterprise slate dark, constantes tipográficas, espaciados y funciones helper para estados semánticos y epistémicos.
- **Preparación de Firma de Medios ONVIF (`src/evidence/models.py`):**
  - Soporte para `signing_status` (`SOURCE_UNSIGNED`, `SIGNED_UNVERIFIED`, `SIGNED_VALID`, `SIGNATURE_INVALID`) y metadatos de procedencia.
- **Motor de Búsqueda Semántica Bajo Demanda (`src/evidence/index.py`):**
  - Clase `SemanticInvestigationEngine` para búsquedas históricas acotadas y enlaces fuente tipo `dvr://site/camera?t=timestamp`.
- **Pruebas Unitarias de Productización y Hardening:**
  - `tests/test_ux_productization.py` y `tests/test_production_hardening.py`.

#### Modificado
- **`src/ui/tk_operational_panels.py`:**
  - Refactorizado para utilizar `DesignTokens` e `I18n`.
  - Eliminados todos los valores sintéticos o inventados (`0.88`, `Zone-XX`, etc.), reemplazados por estados nominales limpios (`SIN SITUACIONES ACTIVAS`, `COLA DE ATENCIÓN VACÍA`).
- **`src/ui/tk_view.py`:**
  - Integración de `DesignTokens` y localización completa `es-CL`.
  - HUD de Focus HD en español con distinción estricta entre `FUENTE`, `PRESENTACIÓN`, `INFERENCIA` y `PERFIL: PRINCIPAL (HD)`.
- **`src/visualization/operational_intelligence.py`:**
  - Extendido `EvidenceBundleViewItem` con atributos de firma ONVIF.

#### Corregido
- Eliminación de falsos estados "ONLINE" en cuadros congelados mediante verificación de avance de secuencia.
- Consistencia del layout de cuadrícula 6 (1 principal 2x2 + 5 auxiliares 1x1).
