# Matriz de Capacidades y Madurez del Producto — TukeVision

**Versión:** 3.0 (F12 Consolidado · TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04)
**Filosofía:** Cero Inteligencia Fabricada · Local-First · Telemetría Factual Directa

---

## 1. Matriz de Madurez de Capacidades

| Capacidad / Subsistema | Implementada | Tests | Física | Certificada | Estado |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Grid Multicámara (1..16 Canales)** | Sí | Sí (955 tests) | Sí (Telemetría directa SourceManager) | Sí | `OPERATIONAL_STABLE` |
| **Focus HD con Selección MAIN** | Sí | Sí | Sí (1080p profile switch real) | Sí | `OPERATIONAL_STABLE` |
| **Aceleración Edge OpenVINO / CPU** | Sí | Sí | Sí (Intel Iris Xe / CPU) | Sí | `OPERATIONAL_STABLE` |
| **Rastreo ByteTrack Multi-Target** | Sí | Sí | Sí (Flujo real multi-cámara) | Sí | `OPERATIONAL_STABLE` |
| **Sistema de Diseño (DesignTokens)** | Sí | Sí | Sí (Tkinter Enterprise Dark) | Sí | `OPERATIONAL_STABLE` |
| **Localización Completa (`es-CL`)** | Sí | Sí | Sí (100% vistas y HUDs) | Sí | `OPERATIONAL_STABLE` |
| **Panel Técnico Colapsable (Video ≥ 80%)** | Sí | Sí | Sí (86.4% área útil de video) | Sí | `OPERATIONAL_STABLE` |
| **Bóveda de Evidencias (Clips MP4+JSON)**| Sí | Sí | Sí (Persistencia atómica) | Sí | `OPERATIONAL_STABLE` |
| **Hash de Integridad Local (SHA-256)** | Sí | Sí | Sí (Verificación criptográfica) | Sí | `OPERATIONAL_STABLE` |
| **Búsqueda Estructurada SQLite (`dvr://`)**| Sí | Sí | Sí (Filtros multidimensionales)| Sí | `OPERATIONAL_STABLE` |
| **Contrato de Firma de Medios ONVIF** | Sí | Sí | No (Gated sin hardware) | No | `CONTRACT_READY / NO_DEVICE` |
| **Búsqueda Semántica / NLP Histórico** | Parcial | Sí (Estructuras de consulta)| No (En roadmap) | No | `TARGET / CONTRACT_READY` |
| **Gobernanza de Autonomía (Policy)** | Sí | Sí | Sí (Autonomía 0 y 1 gobernada) | Sí | `GOVERNED_RUNTIME` |
| **Estado del Agente Cognitivo** | Sí | Sí | Según controlador conectado | Sí | `CONDITIONAL / TRUTHFUL` |
| **Geometría y Plano Espacial 2D** | Sí (Lógica) | Sí | Requiere CAD/SVG por tienda | No | `LOGICAL_COVERAGE` |

---

## 2. Contrato de Verdad Operacional

1. **Cero Datos Fabricados:**
   - La interfaz de usuario nunca sintetiza situaciones a partir de simples detecciones, eventos o cadenas de texto (`DETECTION != TRACK != EVENT != SITUATION`).
   - Si no existe un `SituationRecord` genuino emitido por el backend, la vista muestra formalmente `SIN SITUACIONES ACTIVAS`.
   - La UI nunca genera `situation_id`, `situation_type`, ni deduce severidad ni estado epistémico por confianza.
   - Zonas no configuradas se reportan como `No determinada` (`UNKNOWN`), nunca con identificadores ficticios (`Zona 01`).
   - Estados de agente no conectados se presentan como `ESTADO DEL AGENTE: NO DISPONIBLE`.
   - Autonomías no certificadas por política activa se presentan como `AUTONOMÍA: NO CERTIFICADA`.
   - Estados de salud de sistema se reportan como `NO DETERMINADO` si no existe reporte agregado real.

2. **Integridad de Evidencia vs. Firma de Origen:**
   - El cálculo local de SHA-256 certifica la integridad del archivo persistido en el host local (`LOCAL_FILE_INTEGRITY_HASH`).
   - Las grabaciones procedentes de DVRs o cámaras estándar sin criptografía en hardware se reportan como `FUENTE NO FIRMADA (DVR LOCAL)`.
   - El contrato de firma ONVIF (`SOURCE_UNSIGNED`, `SIGNED_UNVERIFIED`, `SIGNED_VALID`, `SIGNATURE_INVALID`) está preparado y tipado en código para activar validación en cuanto se conecten dispositivos compatibles.

3. **Trazabilidad TES V3:**
   - Toda capacidad declarada en esta matriz mapea 1:1 con `TES/CAPABILITY_MATRIX.md` y cuenta con código, prueba automatizada y artefacto físico de respaldo en `evidence/TV-F12-PHYSICAL-RUNTIME-RECERTIFICATION-04/`.
