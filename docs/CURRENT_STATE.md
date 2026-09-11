# Estado Actual del Sistema — TukeVision (Cierre Pasivo Puro F12)

**ID de Ejecución:** `TV-F12-PASSIVE-OBSERVER-TRUTH-CLOSURE-08`
**Rama:** `phase12/operational-intelligence-visualization-hd`
**Idioma Primario:** Español (`es-CL`)
**Arquitectura:** Local-First / Edge-First (Grabación Primaria en DVR/NVR)
**Marco de Gobernanza:** TES V3 (`TES/`)
**Estado Final de Certificación:** `TV_F12_RUNTIME_TRUTH_CLOSED_WITH_EXTERNAL_LIMITATIONS`

---

## 1. Resumen Ejecutivo

TukeVision opera como un Centro de Mando local de alta fidelidad, integrando 15 canales de video concurrentes en tiempo real, detección y rastreo perimetral/comercial acelerado por OpenVINO/CPU, y visualización operativa estructurada.

### Principios Operacionales Aplicados:
1. **Verdad Epistémica Absoluta:** Todo dato operacional distingue explícitamente entre `HECHO` (detección validada, telemetría física), `INFERENCIA` (clasificación algorítmica probabilística) y `DESCONOCIDO` (parámetros no determinados).
2. **Cero Datos Falsos (Zero-Fake Absolute):** Se eliminó cualquier generación artificial de situaciones, IDs, severidades o diagnósticos globales no justificados en capas de renderizado.
3. **Observador Pasivo de Telemetría Real:** Certificación acoplada pasivamente a los artefactos y estado del proceso operador activo (PID 21032) sin inyectar fallbacks.
4. **Validación Factual de Liveness:** Cámaras observadas en estado `ONLINE` en sub-stream (352x240) con secuencias de avance y pintado continuo en interfaz.
5. **Geometría Grid 6 Verificada Físicamente:** Viewport medido a 1260x593 con 6 celdas reales, 0 solapamiento, 0 recorte y 2.3% de espacio muerto.
6. **UX Simplificada y Dominancia del Video:** El panel lateral técnico es colapsable por defecto (`self._side_panel_visible = False`), garantizando que el área de video ocupe ≥ 80% del espacio visual. Los estados vacíos presentan tarjetas compactas y elegantes de 380px con iconografía nominal.
7. **Trazabilidad Forense Local:** Paquetes de evidencia con cálculo de integridad SHA-256 e indicación honesta de estado de firma de origen.

---

## 2. Inventario de Estados por Módulo

| Módulo | Ruta Principal | Estado de Madurez |
| :--- | :--- | :--- |
| **Núcleo de Interfaz** | `src/ui/tk_view.py` | `OPERACIONAL / CERTIFICADO` |
| **Paneles de Operación** | `src/ui/tk_operational_panels.py` | `OPERACIONAL / ZERO-FAKE VALIDATED` |
| **Tokens de Diseño** | `src/ui/design_tokens.py` | `CONSOLIDADO / CERTIFICADO` |
| **Localización** | `src/localization/i18n.py` | `CONSOLIDADO / es-CL CERTIFICADO` |
| **Indexación SQLite** | `src/evidence/index.py` | `OPERACIONAL / CONTRACT_READY (P0-65)` |
| **Modelos Forenses** | `src/evidence/models.py` | `OPERACIONAL / ONVIF_CONTRACT_READY` |
| **Aceleración Inferencia**| `src/pipeline/` | `OPERACIONAL / OPENVINO VALIDATED` |
| **Gobernanza TES V3** | `TES/` | `CONSOLIDADO / RECONCILIADO` |

---

## 3. Pruebas de Regresión

- **984 pruebas pasadas** (0 fallidas, 0 errores, 4 omitidas, 15 subtests pasados) en 88.03 segundos.
- Suite automatizada cubre `test_strict_runtime_truth.py` validando la prohibición de fallbacks y la derivación booleana estricta de estados PASS/FAIL.
