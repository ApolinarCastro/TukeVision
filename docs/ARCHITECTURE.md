# ARQUITECTURA TÉCNICA DE TUKEVISION (ARCHITECTURE)

**Versión:** 3.0 (F12 Consolidado)  
**Entorno:** Python 3.12+ · Tkinter · OpenVINO · OpenCV · PyAV · SQLite  

---

## 1. Diagrama de Flujo del Pipeline Edge

```
[ Cámaras RTSP / Archivos de Video ]
                 │
                 ▼ (H.264 / H.265 Hardware/Software Ingestion)
[ Frame Queue & Liveness Monitor ] ───► [ Stale Detector & Freshness p50/p95 ]
                 │
                 ├───────────────────────────────────────────┐
                 ▼ (Substream / Bounded Scale)               ▼ (Main HD)
     [ Detección de Movimiento ]                     [ Buffer de Cuadros HD ]
                 │                                           │
                 ▼                                           │
     [ Detector Edge (OpenVINO / YOLO) ]                     │
                 │                                           │
                 ▼                                           │
     [ ByteTrack & Asociación Espacial ]                     │
                 │                                           │
                 ▼                                           │
     [ Analítica Temporal & Permanencia ]                    │
                 │                                           │
                 ▼                                           │
     [ Motor de Situaciones & Reglas ]                       │
                 │                                           │
                 ▼                                           ▼
     [ Empaquetador de Evidencias ] ◄────────────────────────┘
                 │ (Clip PyAV + Cuadro Clave + Hash SHA-256 + Sidecar JSON)
                 ▼
     [ Índice Semántico Ligero (SQLite) ]
                 │
                 ▼
     [ TkApp Command Center UI ] ◄─── [ DesignTokens & i18n (es-CL) ]
```

---

## 2. Componentes Principales

### 2.1 Ingesta y Captura Multicámara (`src/capture/`)
- Mantiene hilos dedicados de captura por cámara.
- Cola de tamaño acotado (`maxsize=2..5`) para garantizar que la interfaz siempre procese el cuadro más reciente sin acumulación de latencia ni fugas de memoria.
- Detección de desconexión y reconexión con backoff exponencial.

### 2.2 Inferencia y Detección en el Borde (`src/detection/`)
- Soporte para aceleración OpenVINO en procesadores Intel/AMD y fallback automático a CPU.
- Procesamiento en resolución optimizada para inferencia (e.g. 640x360), preservando la resolución nativa de la cámara (1080p/4K) para la visualización en foco y la evidencia.

### 2.3 Seguimiento y Análisis Temporal (`src/tracking/`)
- ByteTrack asigna identificadores persistentes (`track_id`) a personas detectadas a lo largo de los cuadros.
- Cálculo acumulativo de tiempo de permanencia (`dwell_time`) en zonas calibradas de la tienda.

### 2.4 Bóveda de Evidencia y Firma de Medios (`src/evidence/`)
- Grabación atómica de clips en MP4 utilizando PyAV.
- Cálculo de hash SHA-256 sobre cada archivo de video e imagen.
- Preparación para firma ONVIF (`SOURCE_UNSIGNED` por defecto en DVRs convencionales).
- Índice SQLite ligero (`data/evidence_index.db`) para búsquedas semánticas e investigación histórica bajo demanda, evitando la sobrecarga de indexar 24/7 flujos continuos innecesarios.

### 2.5 Interfaz de Usuario Operacional (`src/ui/`)
- Construida en Tkinter puro, con renderizado directo sobre canvas para alto rendimiento sin dependencias pesadas de navegador.
- Modos operacionales:
  1. `RESUMEN`: Vista ejecutiva con KPIs en vivo, situaciones activas y cola de atención priorizada.
  2. `EN VIVO`: Cuadrícula multicámara interactiva (1, 4, 6, 9, 16 cámaras) con detección de clics y doble clic para Foco HD.
  3. `SITUACIONES`: Listado detallado de alertas con clasificación de Hechos, Inferencias y Desconocidos.
  4. `INVESTIGACIONES`: Auditoría del razonamiento del agente en cascada.
  5. `EVIDENCIA`: Tabla de auditoría forense con verificación de hashes.
  6. `MAPA / ZONAS`: Vista espacial con cobertura de cámaras por zona física.
  7. `ESTADO DEL SISTEMA`: Telemetría de host (CPU, RAM, Disco) y tabla de estado por flujo de cámara.
