# Estado Actual del Sistema — TukeVision (F12 Consolidado)

**ID de Ejecución:** `TV-F12-SURGICAL-TRUTH-UX-CORRECTION-02`  
**Rama:** `phase12/operational-intelligence-visualization-hd`  
**Idioma Primario:** Español (`es-CL`)  
**Arquitectura:** Local-First / Edge-First (Grabación Primaria en DVR/NVR)  

---

## 1. Resumen Ejecutivo

TukeVision opera como un Centro de Mando local de alta fidelidad, integrando hasta 16 canales de video en tiempo real, detección y rastreo perimetral/comercial acelerado por OpenVINO/CPU, y visualización operativa estructurada.

### Principios Operacionales Aplicados:
1. **Verdad Epistémica:** Todo dato operacional distingue explícitamente entre `HECHO` (detección validada, telemetría física), `INFERENCIA` (clasificación algorítmica probabilística) y `DESCONOCIDO` (parámetros no determinados).
2. **Cero Datos Falsos:** Se eliminó cualquier generación artificial de situaciones o zonas en capas de renderizado.
3. **UX Simplificada y Dominancia del Video:** El panel lateral técnico es colapsable por defecto, garantizando que el área de video ocupe ≥ 80% del espacio visual.
4. **Trazabilidad Forense Local:** Paquetes de evidencia con cálculo de integridad SHA-256 e indicación honesta de estado de firma de origen.

---

## 2. Inventario de Estados por Módulo

| Módulo | Ruta Principal | Estado de Madurez |
| :--- | :--- | :--- |
| **Núcleo de Interfaz** | `src/ui/tk_view.py` | `OPERACIONAL / CERTIFICADO` |
| **Paneles de Operación** | `src/ui/tk_operational_panels.py` | `OPERACIONAL / ZERO-FAKE VALIDATED` |
| **Tokens de Diseño** | `src/ui/design_tokens.py` | `CONSOLIDADO / CERTIFICADO` |
| **Localización** | `src/localization/i18n.py` | `CONSOLIDADO / es-CL CERTIFICADO` |
| **Indexación SQLite** | `src/evidence/index.py` | `OPERACIONAL / CONTRACT_READY` |
| **Modelos Forenses** | `src/evidence/models.py` | `OPERACIONAL / ONVIF_CONTRACT_READY` |
| **Aceleración Inferencia**| `src/pipeline/` | `OPERACIONAL / OPENVINO VALIDATED` |

---

## 3. Pruebas de Regresión

- Suite completa de pruebas unitarias, de integración y visuales sin fallos.
- Pruebas negativas dedicadas garantizan que el rastreo no genera falsas alarmas y que campos ausentes se presentan como no disponibles.
