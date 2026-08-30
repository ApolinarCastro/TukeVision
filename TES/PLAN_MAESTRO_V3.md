# Plan Maestro V3 — TukeVision (F12 Cierre Estricto de Verdad de Runtime)

**ID de Ejecución:** `TV-F12-STRICT-RUNTIME-TRUTH-ENFORCEMENT-06`
**Versión:** 3.0
**Línea Base:** Fase 12 Consolidada (F13 Prohibido)
**Veredicto Final:** `TV_F12_RUNTIME_TRUTH_CLOSED_WITH_EXTERNAL_LIMITATIONS`

---

## 1. Visión y Arquitectura General

TukeVision V3 es una plataforma de software para centros de comando de videovigilancia retail y prevención de pérdidas que opera de manera **local-first** en hardware commodity (CPU x86_64 / Intel Iris Xe / AMD Ryzen).

### Principios Fundacionales Estrictos:
1. **Límite de Grabación Primaria:** La grabación continua y retención masiva de video es responsabilidad del DVR/NVR existente (`dvr://`). TukeVision no duplica el almacenamiento NVR; preserva atómicamente paquetes de evidencia forense indexados.
2. **Cero Inteligencia Fabricada (Zero-Fake Absolute):** Todo dato presentado es `HECHO (FACT)` verificado físicamente, `INFERENCIA (INFERENCE)` determinista o `DESCONOCIDO (UNKNOWN)`. Detección / Rastreo ≠ Situación.
3. **Dominancia Visual:** En visualización en vivo, el video ocupa ≥ 80% del área de trabajo (86.4% medido), manteniendo los paneles técnicos colapsables por defecto.
4. **Verificación Física Genuina:** Toda evidencia y telemetría proviene de objetos reales del runtime compartidos en el mismo espacio de memoria (`SourceManager`, `TkApp`, `ResourceTelemetry`, `TrueLiveness`) con soak continuo de 1800s.

---

## 2. Taxonomía Formal de Madurez

| Estado | Definición |
| :--- | :--- |
| **`CERTIFIED`** | Código implementado, probado exhaustivamente con tests automáticos (100% PASS) y validado sobre el runtime activo de TukeVision (`TV-F12-STRICT-RUNTIME-TRUTH-ENFORCEMENT-06`). |
| **`PHYSICALLY_VALIDATED`** | Implementado y comprobado con conmutación real de flujo en runtime; sujeto a disponibilidad de streams HD de red externa. |
| **`TESTED`** | Implementado y con suite de pruebas unitarias/integración completa (100% PASS) en entornos locales. |
| **`IMPLEMENTED`** | Código completo y tipado en repositorio, pendiente de pruebas de regresión ampliadas. |
| **`CONTRACT_READY`** | Modelos de datos, interfaces y contratos tipados listos para interoperar, con ejecución en hardware pendiente de periféricos (e.g. cámaras firmantes). |
| **`PARTIAL`** | Subsistema con componentes base funcionales (e.g. búsqueda estructurada SQLite) y componentes avanzados planificados (e.g. VLM NLP). |
| **`TARGET`** | Capacidad estratégica en hoja de ruta formal, no disponible en el runtime local actual. |
| **`RESERVED`** | Capacidad arquitectónicamente compatible pero deliberadamente no priorizada para el perfil edge actual. |
| **`REJECTED`** | Tecnología o patrón evaluado formalmente y descartado por sobrecarga o conflicto de diseño. |

---

## 3. Estado de los Subsistemas Clave

1. **Ingesta & Grid Multicámara (1..16 canales):** `CERTIFIED` (Estable en 1, 4, 6, 9 y 16 canales; Grid 6 medido físicamente a 1260x593 con 0 solapes y 0 recorte).
2. **Foco HD con Selección de Perfil MAIN:** `PHYSICALLY_VALIDATED / EXTERNAL_LIMITATION` (Conmutación a subtype 0 nativo sin upscale artificial; stream no entregado por hardware externo fuera de línea).
3. **Inferencia Edge OpenVINO:** `CERTIFIED` (Aceleración CPU/iGPU con fallback automático).
4. **Rastreo ByteTrack:** `CERTIFIED` (Seguimiento continuo de identidades y permanencias).
5. **Gobernanza de Autonomía & Acciones:** `CERTIFIED` (Políticas de autonomía 0 y 1 con aprobación del operador).
6. **Sistema de Diseño (DesignTokens) & Localización (`es-CL`):** `CERTIFIED`.
7. **Bóveda de Evidencia & Hash SHA-256 Local:** `CERTIFIED`.
8. **Búsqueda Estructurada de Evidencias (SQLite + `dvr://`):** `TESTED / OPERATIONAL`.
9. **Firma de Medios ONVIF:** `CONTRACT_READY` (Contratos listos, validación física no disponible por hardware de cámaras).
10. **Búsqueda Semántica / NLP Histórico:** `TARGET / EVOLUTION` (Búsqueda estructurada operativa; NLP en roadmap).
