# Matriz de Capacidades y Madurez del Producto — TukeVision

**Versión:** 3.0 (F12 Consolidado · TV-F12-SURGICAL-TRUTH-UX-CORRECTION-02)  
**Filosofía:** Cero Inteligencia Fabricada · Local-First · Integridad Factual  

---

## 1. Matriz de Madurez de Capacidades

| Capacidad / Subsistema | Implementada | Pruebas Unitarias/Integración | Validación Física Hardware | Nivel de Certificación | Estado Canónico |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Grid Multicámara 1..16 Canales** | Sí | Sí (940+ tests) | Sí (DVR Hikvision/Dahua) | CERTIFICADA | `OPERATIONAL_STABLE` |
| **Focus HD con Selección de Perfil MAIN** | Sí | Sí | Sí (1080p RTSP directo) | CERTIFICADA | `OPERATIONAL_STABLE` |
| **Aceleración Edge con OpenVINO / CPU** | Sí | Sí | Sí (Intel Iris Xe / CPU) | CERTIFICADA | `OPERATIONAL_STABLE` |
| **Rastreo ByteTrack Multi-Target** | Sí | Sí | Sí (Escenas de tienda) | CERTIFICADA | `OPERATIONAL_STABLE` |
| **Sistema de Diseño Unificado (DesignTokens)** | Sí | Sí | Sí (Tkinter Enterprise Dark) | CERTIFICADA | `OPERATIONAL_STABLE` |
| **Localización Completa al Español (`es-CL`)** | Sí | Sí | Sí (100% vistas y HUDs) | CERTIFICADA | `OPERATIONAL_STABLE` |
| **Panel Técnico Colapsable (Video Dominante)** | Sí | Sí | Sí (Área útil ≥ 80%) | CERTIFICADA | `OPERATIONAL_STABLE` |
| **Bóveda de Evidencias (Paquetes Locales)** | Sí | Sí | Sí (Clips MP4 + JSON) | CERTIFICADA | `OPERATIONAL_STABLE` |
| **Hash de Integridad Local (SHA-256)** | Sí | Sí | Sí (Cuadros y Metadatos) | CERTIFICADA | `OPERATIONAL_STABLE` |
| **Búsqueda Estructurada de Evidencias (SQLite)** | Sí | Sí | Sí (Filtros tiempo/cámara/tag) | IMPLEMENTADA | `OPERATIONAL_STABLE` |
| **Enlaces Directos de Origen (`dvr://`)** | Sí | Sí | Sí (Rutas URI acotadas) | IMPLEMENTADA | `OPERATIONAL_STABLE` |
| **Contrato de Firma de Medios ONVIF** | Sí | Sí | No (Requiere cámara firmante) | CONTRATO LISTO | `CONTRACT_READY / NO_DEVICE` |
| **Análisis Histórico Semántico / NLP** | Parcial | Sí (Estructuras de consulta) | No (Bajo demanda en roadmap) | PARCIAL | `TARGET / CONTRACT_READY` |
| **Gobernanza de Autonomía (Policy Engine)** | Sí | Sí | Sí (Autonomía 0 y 1 gobernada) | SEGÚN POLÍTICA | `GOVERNED_RUNTIME` |
| **Estado del Agente Cognitivo** | Sí | Sí | Según controlador conectado | SEGÚN CONTROLADOR | `CONDITIONAL / TRUTHFUL` |
| **Geometría y Plano Espacial 2D** | Sí (Lógica) | Sí | Requiere CAD/SVG por tienda | COBERTURA LÓGICA | `LOGICAL_COVERAGE` |

---

## 2. Contrato de Verdad Operacional

1. **Cero Datos Fabricados:**
   - La interfaz de usuario nunca sintetiza situaciones a partir de simples detecciones o rastreos (`DETECTION != TRACK != SITUATION`).
   - Si no existe un `SituationRecord` genuino emitido por el backend, la vista muestra formalmente `SIN SITUACIONES ACTIVAS`.
   - Zonas no configuradas se reportan como `No determinada` (`UNKNOWN`), nunca con identificadores ficticios (`Zona 01`).
   - Estados de agente no conectados se presentan honestamente como `ESTADO DEL AGENTE: NO DISPONIBLE`.
   - Autonomías no certificadas por política activa se presentan como `AUTONOMÍA: NO CERTIFICADA`.

2. **Integridad de Evidencia vs. Firma de Origen:**
   - El cálculo local de SHA-256 certifica la integridad del archivo persistido en el host local (`LOCAL_FILE_INTEGRITY_HASH`).
   - Las grabaciones procedentes de DVRs o cámaras estándar sin criptografía en hardware se reportan como `FUENTE NO FIRMADA (DVR LOCAL)`.
   - El contrato de firma ONVIF (`SOURCE_UNSIGNED`, `SIGNED_UNVERIFIED`, `SIGNED_VALID`, `SIGNATURE_INVALID`) está preparado y tipado en código para activar validación en cuanto se conecten dispositivos compatibles.

3. **Búsqueda Estructurada vs. Búsqueda Semántica:**
   - **Capacidad Actual:** Búsqueda estructurada multidimensional sobre SQLite indexado localmente (tienda, cámara, ventana de tiempo, etiqueta, confianza, enlaces `dvr://`).
   - **Capacidad en Evolución:** Búsqueda en lenguaje natural con análisis VLM bajo demanda sobre grabaciones históricas de DVR.
