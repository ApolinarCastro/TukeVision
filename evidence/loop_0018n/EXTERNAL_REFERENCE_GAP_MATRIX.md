# LOOP-0018N — EXTERNAL_REFERENCE_GAP_MATRIX (PASO 4)

Para cada referencia ya investigada/documentada responder:
WHAT_CAPABILITY_IT_PROVES | WHAT_PATTERN_WE_CAN_REUSE | WHETHER_CODE_INTEGRATION_IS_NEEDED |
LICENSE_OR_DEPENDENCY_RISK | WHETHER_IT_SOLVES_A_REAL_TUKEVISION_GAP.

## Referencias documentadas en TES/portable

### 1. SmartPSS Lite (reverse engineering)
- **Capability:** gestión DVR/NVR multi-cámara, grid multiview, selector de canal/subtype.
- **Patrón reutilizable:** modelo de canal 1-16 + subtype main/sub; separación UI vs backend de captura.
- **Integración código:** NO (fue una prueba discriminante LOOP-0018F; no se importa).
- **Riesgo:** NO aplica (no se integra). SmartPSS fue B1_INCONCLUSIVE (crash histórico de TukeVision, no de SmartPSS).
- **Gap real:** VALIDA el modelo de 16 canales → apoya SourceManager y el grid 4x4. NO requiere código.

### 2. Pyresearch projects (CNN/activity/interaction/people flow)
- **Capability:** demostración de reconocimiento de actividades/interacciones y flujo de personas con CNNs.
- **Patrón reutilizable:** concepto de Activity Layer sobre detección+tracking (no el código).
- **Integración código:** NO (videos de demostración, sin integración verificable).
- **Riesgo:** desconocido/indeterminado (no se adopta).
- **Gap real:** ORIENTA la taxonomía de actividad (ENTER/EXIT/DWELL/LOITER/APPROACH/WATCH/TOUCH/RETURN). No resuelve un gap de código hoy.

### 3. OpenCV (captura/visión/zona/evidencia)
- **Capability:** todo el núcleo de captura/geometría/anotación ya en uso.
- **Patrón reutilizable:** activo y certificado.
- **Integración código:** NO (ya es el stack).
- **Riesgo:** OpenCV 5.0.0.93 activo; NO se modifica.
- **Gap real:** NO (cubierto).

### 4. Ultralytics/YOLO (detección)
- **Capability:** detección de personas (YOLO11n).
- **Patrón reutilizable:** activo y certificado; también backbone para ReID (E-03).
- **Integración código:** NO (ya es el stack).
- **Riesgo:** AGPL-3.0 (Ultralytics). Dependencia ya aceptada en DEC-0023.
- **Gap real:** NO (cubierto). En E-03 se reutilizaría su `model.embed()`.

### 5. ByteTrack (tracking)
- **Capability:** seguimiento temporal.
- **Patrón reutilizable:** activo (paquete `trackers` ByteTrackTracker).
- **Integración código:** NO (ya es el stack).
- **Riesgo:** MIT (trackers). Aceptado en DEC-0023.
- **Gap real:** NO (cubierto). Para multicámara, un tracker por cámara (namespace por cámara).

### 6. CNN / activity recognition
- **Capability:** reconocimiento de actividad sobre video.
- **Patrón reutilizable:** Activity Layer como capa POST tracking (especificada en ACTIVITY_LAYER_SPEC).
- **Integración código:** NO hoy.
- **Riesgo:** depende de modelo/entrenamiento → fuera del alcance (sin entrenamiento de modelos).
- **Gap real:** PARCIAL — la taxonomía es un gap de producto, pero la implementación queda DISEÑADA, no desarrollada.

### 7. People flow
- **Capability:** conteo de entradas/salidas/ocupación.
- **Patrón reutilizable:** FlowCounter de E-02 (trajectory.py) ya implementa IN/OUT/INSIDE por zona.
- **Integración código:** REUSE E-02 (adaptación multicámara), NO ahora.
- **Riesgo:** ninguno (0 libs nuevas).
- **Gap real:** CERRADO por diseño con E-02 (PRIO 3).

### 8. Warden / Open-Source Face Recognition SDK
- **Capability:** reconocimiento facial (prohibido por DEC-0013).
- **Patrón reutilizable:** NINGUNO aplicable a TukeVision (decisión de privacidad).
- **Integración código:** NO. **REJECTED por gobernanza.**
- **Riesgo:** legal/privacidad (DEC-0013).
- **Gap real:** NO. Contradice el modelo (observa procesos, no personas).

### 9. CactusCompute Hybrid
- **Capability:** computación híbrida (edge + cloud) para video AI.
- **Patrón reutilizable:** la separación de determinista (edge) vs razonamiento (capa superior) es
  coherente con AI_POLICY (CV determinista + AI reasoning opcional).
- **Integración código:** NO hoy.
- **Riesgo:** no evaluado (referencia conceptual).
- **Gap real:** PARCIAL — solo valida el patrón de AI_POLICY.

### 10. Qwen MM Plugins
- **Capability:** modelos multimodales (visión+texto) para explicación de eventos.
- **Patrón reutilizable:** AI second opinion sobre candidatos de evento (AI_POLICY).
- **Integración código:** NO. Qwen está REJECTED en TES (DEC-0023, TECHNOLOGY_STACK_MVP no instalar).
- **Riesgo:** API/red/licencia; contradice política local.
- **Gap real:** PARCIAL — el gap es "AI second opinion", pero su resolución NO es Qwen (rejected);
  queda como especificación, sin dependencia.

### 11. NVIDIA / DeepStream (Context-Aware Video AI)
- **Capability:** multi-cámara/GPU/DeepStream/agentes.
- **Patrón reutilizable:** modelo mental Video→Observación→Evento→Contexto→Decisión→Acción
  (ADOPTED conceptualmente); DeepStream NO.
- **Integración código:** NO. REJECTED/FUTURE con trigger (necesidad multi-cámara/GPU/escala).
- **Riesgo:** infraestructura empresarial/GPU; fuera de alcance.
- **Gap real:** PARCIAL — SourceManager multicámara que construimos es el primer paso del
  camino que DeepStream resolvería a mayor escala; NO se adopta DeepStream.

## Resultado (G4)
- EXTERNAL_REFERENCES_MAPPED_TO_REAL_GAPS = PASS.
- NINGUNA referencia exige integración de código en este LOOP.
- NINGUNA nueva dependencia/licencia se introduce (NEW_DEPENDENCIES = 0).
- Qwen y Face Recognition SDK quedan REJECTED; DeepStream queda FUTURE con trigger.