# Radar de Tecnología — TukeVision V3

El Radar de Tecnología clasifica las tecnologías, bibliotecas y patrones evaluados para el ecosistema TukeVision bajo la gobernanza TES V3.

---

```text
               ▲
               │      ADOPT
               │   • OpenVINO (CPU/iGPU)
               │   • PyAV / H.264 / H.265
               │   • ByteTrack
               │   • Tkinter + DesignTokens
               │   • SQLite Structured Indexing (P0-65)
               │
    ADAPT      │      EVALUATE
 • Ambient.ai UX│   • ONVIF Profile T / Media Signing (CONTRACT_READY)
 • IntelliSeek │   • ONNX Runtime secondary
 • God's Eye   │   • Attention Orchestrator Metrics (P0-66)
 • ClearCam Exp│
───────────────┼────────────────►
    WATCH      │      RESERVE
 • Local VLM   │   • Radar mmWave
 • Semantic NLP│   • Cámaras Térmicas
 • WebRTC Aux  │   • Audio Anómalo
               │
               │      REJECT
               │   • Detectron2 (Edge)
               │   • Chromium/Electron UI
               │   • Grabación continua 24/7 en host
```

---

## 1. Tecnologías en `ADOPT` (Adoptadas en Producción)

| Tecnología / Capacidad | Justificación | Impacto en TukeVision | Estado Actual |
| :--- | :--- | :--- | :--- |
| **OpenVINO Edge Runtime** | Inferencia de alta eficiencia en hardware Intel x86_64 y gráficos integrados Iris Xe. | Permite 25+ FPS en 16 streams sin GPUs dedicadas. | `ADOPTED / CERTIFIED` |
| **PyAV (FFmpeg C-bindings)** | Decodificación y multiplexación de bajo nivel en streaming RTSP. | Baja latencia, selección exacta de perfiles MAIN/SUB. | `ADOPTED / CERTIFIED` |
| **ByteTrack** | Algoritmo de asociación multi-objeto basado en similitud espacial y de movimiento. | Mantiene identidades estables sin sobrecarga de cómputo. | `ADOPTED / CERTIFIED` |
| **DesignTokens (Tkinter Nativo)** | Sistema de diseño declarativo con paleta de alto contraste y temas oscuros. | Cero dependencias pesadas, arranque instantáneo (<1s). | `ADOPTED / CERTIFIED` |
| **Recuperación Estructurada SQLite (P0-65)** | Motor relacional local embebido para eventos, políticas e índices multidimensionales. | Búsqueda estructurada operativa con enlaces `dvr://`. | `IMPLEMENTED / OPERATIONAL` |

---

## 2. Tecnologías en `ADAPT` (Patrones Adaptados sin Código Externo)

| Patrón / Concepto | Origen / Inspiración | Adaptación en TukeVision | Estado Actual |
| :--- | :--- | :--- | :--- |
| **Patrón God's Eye View** | Centros de Mando Avanzados | Cuadrícula conmutativa, HUD de Foco HD y vistas espaciales lógicas. | `ADAPTED` |
| **Patrón Ambient.ai** | Plataformas de IA perimetral | Desglose epistémico explícito (`HECHO`, `INFERENCIA`, `DESCONOCIDO`). | `ADAPTED` |
| **Patrón HiFocus IntelliSeek** | Grabadores NVR HiFocus | Búsqueda estructurada multidimensional con enlace a URIs `dvr://`. | `ADAPTED` |
| **ClearCam RTSP Recovery** | roryclear/clearcam | Resiliencia de decodificador (grace period, single-owner, first-frame). | `ADAPTED` |

---

## 3. Tecnologías en `EVALUATE` (En Evaluación Técnica & Contratos Listos)

| Tecnología / Capacidad | Justificación | Condición de Reevaluación / Validación | Estado |
| :--- | :--- | :--- | :--- |
| **ONVIF Media Signing (Profile T / G)** | Verificación criptográfica de origen directamente en la cámara. | Contrato 100% tipado en código; validación física pendiente de hardware firmante. | `CONTRACT_READY / DEVICE_VALIDATION=PENDING HARDWARE` |
| **Métricas de Orquestador de Atención (P0-66)** | Medición de reducción de carga cognitiva sobre el operador. | Monitoreo de: `ATTENTION_REDUCTION`, `MISSED_RELEVANT_EVENTS`, `FALSE_ESCALATION_RATE`, `TIME_TO_OPERATOR_ATTENTION`, `TIME_TO_INVESTIGATION`. | `EVALUATE / TELEMETRY_ACTIVE` |
| **ONNX Runtime (Fallback)** | Compatibilidad con procesadores AMD y GPUs alternativas. | Requerimiento de despliegue en hardware no-Intel. | `EVALUATE` |

---

## 4. Tecnologías en `WATCH` (En Observación y Evolución Estratégica)

| Tecnología / Capacidad | Justificación | Condición de Reevaluación | Estado Roadmap (P0-65) |
| :--- | :--- | :--- | :--- |
| **Investigación Semántica / NLP Histórico** | Búsqueda semántica en lenguaje natural sobre eventos grabados. | Modelos cuantizados (<2B parámetros) con latencia <500ms en CPU edge. | `TARGET / EVOLUTION` |
| **Analítica de IA On-Demand sobre DVR/NVR** | Extracción e inferencia diferida sobre histórico de video del DVR. | Requiere integración con API de exportación DVR/NVR (`dvr://`). | `TARGET` |
| **WebRTC Gateway Auxiliar** | Visualización remota en navegadores de supervisores. | Requerimiento de acceso web fuera del host físico de mando. | `WATCH` |

---

## 5. Tecnologías en `RESERVE` (Reservadas para Fases Futuras)

| Tecnología | Justificación de Reserva |
| :--- | :--- |
| **Sensores Radar mmWave** | Costo de integración no justificado en tiendas retail estándar. |
| **Cámaras Térmicas Radiométricas** | Reservadas para prevención de incendios o zonas industriales específicas. |
| **Analítica de Audio Anómalo** | Restricciones de privacidad y micrófonos no disponibles en la mayoría de cámaras IP. |

---

## 6. Tecnologías en `REJECT` (Rechazadas Formalmente)

| Tecnología | Motivo de Rechazo | Alternativa Adoptada |
| :--- | :--- | :--- |
| **Detectron2 / Mask R-CNN** | Sobrecarga de memoria (>4GB) y latencia incompatible con CPU edge. | Inferencia OpenVINO con YOLO / ByteTrack. |
| **Frameworks UI con Chromium (Electron/CEF)** | Alto consumo de RAM (>500MB) y lentitud de renderizado en video en vivo. | Interfaz nativa Tkinter optimizada con Canvas/Pillow. |
| **Grabación Continua 24/7 en Host TukeVision** | Saturación de disco y duplicación innecesaria de la función del NVR. | Preservación atómica de paquetes de evidencia + enlaces `dvr://`. |
