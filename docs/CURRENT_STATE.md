# Estado Actual del Sistema — TukeVision (F12 Consolidado & Cierre Físico)

**ID de Ejecución:** `TV-F12-MEGALOOP-RUNTIME-TRUTH-CLOSURE-05`
**Rama:** `phase12/operational-intelligence-visualization-hd`
**Idioma Primario:** Español (`es-CL`)
**Arquitectura:** Local-First / Edge-First (Grabación Primaria en DVR/NVR)
**Marco de Gobernanza:** TES V3 (`TES/`)

---

## 1. Resumen Ejecutivo

TukeVision opera como un Centro de Mando local de alta fidelidad, integrando hasta 16 canales de video en tiempo real, detección y rastreo perimetral/comercial acelerado por OpenVINO/CPU, y visualización operativa estructurada.

### Principios Operacionales Aplicados:
1. **Verdad Epistémica Absoluta:** Todo dato operacional distingue explícitamente entre `HECHO` (detección validada, telemetría física), `INFERENCIA` (clasificación algorítmica probabilística) y `DESCONOCIDO` (parámetros no determinados).
2. **Cero Datos Falsos (Zero-Fake Absolute):** Se eliminó cualquier generación artificial de situaciones, IDs, severidades o diagnósticos globales no justificados en capas de renderizado.
3. **Telemetría Directa en Mismo Proceso:** Toda certificación física proviene de mediciones directas sobre los objetos en ejecución del runtime principal (`SourceManager`, `psutil`, `TkApp`, `TrueLiveness`), descartando generadores sintéticos y procesos aislados.
4. **UX Simplificada y Dominancia del Video:** El panel lateral técnico es colapsable por defecto (`self._side_panel_visible = False`), garantizando que el área de video ocupe ≥ 80% del espacio visual. Los estados vacíos presentan tarjetas compactas y elegantes de 380px con iconografía nominal.
5. **Trazabilidad Forense Local:** Paquetes de evidencia con cálculo de integridad SHA-256 e indicación honesta de estado de firma de origen.
6. **Reconciliación TES V3:** Cada componente cuenta con trazabilidad formal `CÓDIGO ↔ PRUEBA ↔ EVIDENCIA FÍSICA REAL ↔ TES`.

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

- 963 pruebas pasadas (0 fallidas, 0 errores, 4 omitidas, 15 subtests pasados).
- Suite automatizada cubre `test_runtime_evidence_collector.py` validando la vinculación directa de runtime y la derivación booleana estricta de estados PASS/FAIL.
