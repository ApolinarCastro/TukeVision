# Registro de Cambios — TukeVision

Todos los cambios notables en este proyecto se documentan en este archivo.

---

## [3.0.0-truth-ux-corrected] - 2026-08-30

### Corregido (Eliminación de Datos Falsos y Verdad Operacional)
- **Eliminación de Situaciones Fabricadas (`src/ui/tk_operational_panels.py`):** Las detecciones y rastreos de objetos ya no se convierten sintéticamente en situaciones o alarmas. Solo se renderizan situaciones si existe un `SituationRecord` formal del backend.
- **Zonas Honestas:** Si una cámara o situación no tiene zona física configurada, se presenta como `No determinada`, eliminando identificadores sintéticos (`Zona 01`).
- **Estado del Agente y Autonomía:** Si el controlador de agente no está activo, se muestra formalmente `ESTADO DEL AGENTE: NO DISPONIBLE` y `AUTONOMÍA: NO CERTIFICADA`.
- **Integridad Local vs. Firma de Origen:** Evidencia local claramente rotulada con `● SHA-256 LOCAL VERIFICADO` y `FUENTE NO FIRMADA (DVR LOCAL)`.

### Mejorado (UX Simplificada y Productización Visual)
- **Panel Técnico Colapsable (`src/ui/tk_view.py`):** El panel lateral de detalles técnicos está colapsado por defecto, permitiendo que la cuadrícula de video ocupe el 100% del ancho del espacio de trabajo (área útil de video ≥ 80%).
- **Botón de Alternancia de Detalles:** Añadido control `Detalles Técnicos ⮞` en la barra inferior para acceder a telemetría técnica bajo demanda.
- **Espaciado y Visualización Compacta:** Botones y tarjetas operacionales compactadas con `DesignTokens` para garantizar visibilidad sin recortes en resoluciones desde 1024x640 hasta 1920x1080.
- **Localización Completa (`es-CL`):** Estados nominales concisos y etiquetas operacionales estandarizadas en español.

### Pruebas y Fixtures
- **Reclasificación de Fixtures Visuales:** Movido generador de capturas sintéticas a `tests/fixtures/ui/generate_ui_fixture_screenshots.py` clasificado como `UI_GOLDEN (synthetic=true)`.
- **Nuevas Pruebas Negativas:** Agregadas pruebas en `tests/test_ux_productization.py` que validan formalmente la ausencia de inteligencia fabricada.
