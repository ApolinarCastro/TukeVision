# Radar de Tecnología — TukeVision V3

El Radar de Tecnología clasifica las tecnologías, bibliotecas y patrones evaluados para el ecosistema TukeVision.

---

```text
               ▲
               │      ADOPT
               │   • OpenVINO (CPU/iGPU)
               │   • PyAV / H.264 / H.265
               │   • ByteTrack
               │   • Tkinter + DesignTokens
               │   • SQLite Indexing
               │
    ADAPT      │      EVALUATE
 • Ambient.ai UX│   • ONVIF Profile T Hardware
 • IntelliSeek │   • ONNX Runtime secondary
 • God's Eye   │
───────────────┼────────────────►
    WATCH      │      RESERVE
 • Local VLM   │   • Radar mmWave
 • WebRTC Aux  │   • Cámaras Térmicas
               │   • Audio Anómalo
               │
               │      REJECT
               │   • Detectron2 (Edge)
               │   • Chromium/Electron UI
               │   • Grabación continua 24/7 en host
```

---

## 1. Tecnologías en `ADOPT` (Adoptadas en Producción)

| Tecnología | Justificación | Impacto en TukeVision | Estado Actual |
| :--- | :--- | :--- | :--- |
| **OpenVINO Edge Runtime** | Inferencia de alta eficiencia en hardware Intel x86_64 y gráficos integrados Iris Xe. | Permite 25+ FPS en 16 streams sin GPUs dedicadas. | `ADOPTED / CERTIFIED` |
| **PyAV (FFmpeg C-bindings)** | Decodificación y multiplexación de bajo nivel en streaming RTSP. | Baja latencia, selección exacta de perfiles MAIN/SUB. | `ADOPTED / CERTIFIED` |
| **ByteTrack** | Algoritmo de asociación multi-objeto basado en similitud espacial y de movimiento. | Mantiene identidades estables sin sobrecarga de cómputo. | `ADOPTED / CERTIFIED` |
| **DesignTokens (Tkinter Nativo)** | Sistema de diseño declarativo con paleta de alto contraste y temas oscuros. | Cero dependencias pesadas, arranque instantáneo (<1s). | `ADOPTED / CERTIFIED` |
| **SQLite Estructurado** | Motor relacional local embebido para eventos, políticas e índices. | Trazabilidad local-first sin servidores externos. | `ADOPTED / CERTIFIED` |

---

## 2. Tecnologías en `ADAPT` (Patrones Adaptados sin Código Externo)

| Patrón / Concepto | Origen / Inspiración | Adaptación en TukeVision | Estado Actual |
| :--- | :--- | :--- | :--- |
| **Patrón God's Eye View** | Centros de Mando Avanzados | Cuadrícula conmutativa, HUD de Foco HD y vistas espaciales lógicas. | `ADAPTED` |
| **Patrón Ambient.ai** | Plataformas de IA perimetral | Desglose epistémico explícito (`HECHO`, `INFERENCIA`, `DESCONOCIDO`). | `ADAPTED` |
| **Patrón HiFocus IntelliSeek** | Grabadores NVR HiFocus | Búsqueda estructurada multidimensional con enlace a URIs `dvr://`. | `ADAPTED` |

---

## 3. Tecnologías en `EVALUATE` (En Evaluación Técnica)

| Tecnología | Justificación | Condición de Reevaluación |
| :--- | :--- | :--- |
| **ONVIF Profile T Hardware Signing** | Verificación criptográfica de origen directamente en la cámara. | Disponibilidad física de cámaras con firmware compatible en sitio piloto. |
| **ONNX Runtime (Fallback)** | Compatibilidad con procesadores AMD y GPUs alternativas. | Requerimiento de despliegue en hardware no-Intel. |

---

## 4. Tecnologías en `WATCH` (En Observación)

| Tecnología | Justificación | Condición de Reevaluación |
| :--- | :--- | :--- |
| **Modelos VLM Locales (Vision-Language)** | Búsqueda semántica en lenguaje natural sobre clips históricos. | Modelos cuantizados (<2B parámetros) con latencia <500ms en CPU. |
| **WebRTC Gateway Auxiliar** | Visualización remota en navegadores de supervisores. | Requerimiento de acceso web fuera del host físico de mando. |

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
