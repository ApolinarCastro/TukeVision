# Registro de Decisiones de Arquitectura (ADR) — TukeVision

Este registro documenta formalmente las decisiones arquitectónicas y tecnológicas materiales adoptadas en TukeVision V3.

---

### [DEC-001] Integración de OpenVINO para Inferencia Edge
- **Estado:** `ADOPTADO`
- **Contexto:** Se requiere procesamiento de visión por computadora en hardware edge estándar sin requerir GPUs discretas costosas.
- **Decisión:** Integrar OpenVINO como runtime de inferencia primario para CPUs Intel x86_64 e iGPUs Iris Xe, con fallback automático a ejecución multihilo CPU.
- **Impacto:** Permite inferencia a 25+ FPS en hasta 16 canales simultáneos con latencia acotada (<40ms).

---

### [DEC-002] Rechazo de Detectron2 para el Perfil Edge Actual
- **Estado:** `RECHAZADO / RESERVADO`
- **Contexto:** Se evaluó el uso de modelos pesados de segmentación basados en Detectron2 (Mask R-CNN).
- **Decisión:** Descartar Detectron2 del perfil de producción edge debido a su alto consumo de memoria (>4GB VRAM) y latencia incompatible con 16 streams concurrentes en CPU.
- **Impacto:** Se preserva la arquitectura liviana con YOLO/ByteTrack optimizados para OpenVINO.

---

### [DEC-003] Adaptación de Patrones God's Eye View & Ambient.ai
- **Estado:** `ADAPTADO (PATRÓN UX / SIN DEPENDENCIA DE CÓDIGO)`
- **Contexto:** Se analizaron interfaces de centros de comando líderes (God's Eye View y Ambient.ai) para mejorar la usabilidad del operador.
- **Decisión:** Adaptar patrones visuales (jerarquía oscura, HUD de Foco HD con separación Fuente/Presentación/Inferencia, panel técnico colapsable y badges epistémicos) directamente en Tkinter con `DesignTokens` nativos, sin importar librerías externas ni crear dependencias de terceros.
- **Impacto:** Experiencia visual de alta gama con cero dependencias pesadas.

---

### [DEC-004] Gobernanza de Acciones y Autonomía por Políticas
- **Estado:** `ADOPTADO`
- **Contexto:** Los agentes de analítica de video deben operar bajo estricto control humano en prevención de pérdidas.
- **Decisión:** Implementar un motor de políticas SQLite que restringe la autonomía (Nivel 0 y 1 gobernado). Cualquier acción de preservación o escalamiento requiere confirmación o registro explícito. Prohibido hardcodear autonomía 2 o 3.
- **Impacto:** Seguridad operacional y trazabilidad legal de cada intervención.

---

### [DEC-005] Límite Arquitectónico: DVR/NVR como Grabador Primario
- **Estado:** `ADOPTADO`
- **Contexto:** TukeVision opera como capa de inteligencia y comando, no como un NVR masivo de grabación continua 24/7.
- **Decisión:** Mantener el límite arquitectónico donde la grabación 24/7 reside en el DVR/NVR existente. TukeVision preserva únicamente paquetes de evidencia forense (clips atómicos + JSON sidecar) y enlaza al historial NVR mediante URIs `dvr://`.
- **Impacto:** Cero saturación de disco local y compatibilidad con cualquier grabador existente.

---

### [DEC-006] Preparación Contractual de Firma de Medios ONVIF (Profile T / G)
- **Estado:** `CONTRACT_READY (VALIDACIÓN FÍSICA NO DISPONIBLE)`
- **Contexto:** Se requiere soporte para validación criptográfica de origen según estándares ONVIF Media Signing.
- **Decisión:** Implementar contratos y enumeraciones completos (`SOURCE_UNSIGNED`, `SIGNED_UNVERIFIED`, `SIGNED_VALID`, `SIGNATURE_INVALID`) en `src/evidence/models.py`. Clasificar el hash SHA-256 local como `LOCAL_FILE_INTEGRITY_HASH` y rotular cámaras estándar como `FUENTE NO FIRMADA (DVR LOCAL)` mientras no exista hardware firmante.
- **Impacto:** Código 100% tipado y listo para autenticación ONVIF sin sobredeclarar compatibilidad física ausente.

---

### [DEC-007] Adaptación de HiFocus IntelliSeek (Búsqueda Estructurada vs. NLP)
- **Estado:** `ADAPTADO (BÚSQUEDA ESTRUCTURADA IMPLEMENTADA / NLP TARGET)`
- **Contexto:** Se evaluó el concepto IntelliSeek de HiFocus para recuperación rápida de eventos históricos.
- **Decisión:** Implementar indexación estructurada en SQLite con filtros por cámara, zona, intervalo temporal y etiquetas con enlaces `dvr://`. Reservar la búsqueda semántica en lenguaje natural (NLP/VLM) como objetivo estratégico futuro (`TARGET`).
- **Impacto:** Búsqueda rápida, determinista y liviana disponible inmediatamente.

---

### [DEC-008] Supervisión de Flujo y Prevención de Falso Verde (Liveness Real)
- **Estado:** `ADOPTADO`
- **Contexto:** Un socket RTSP abierto o un canvas con imagen estática puede engañar al operador simulando un flujo en vivo cuando la cámara se congeló.
- **Decisión:** Exigir avance simultáneo de secuencia de captura, secuencia de presentación y edad acotada de fotogramas (`generation, frame_sequence`). Si la imagen se congela, el estado pasa inmediatamente a `STALE` o `RECONNECTING`.
- **Impacto:** Verdad operacional absoluta en supervisión crítica.

---

### [DEC-009] Tecnologías Reservadas (Radar, Térmica, Audio Analítico)
- **Estado:** `RESERVADO`
- **Contexto:** Sensores adicionales para detección perimetral.
- **Decisión:** Mantener las interfaces de datos abiertas pero no implementar drivers de hardware físico en el perfil retail actual.
- **Impacto:** Concentración de recursos en la robustez del video visual estándar.
