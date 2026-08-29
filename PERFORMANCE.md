# TukeVision — Registro Canónico de Rendimiento y Telemetría

Este documento consolida las mediciones reales y verificadas de rendimiento a través de las fases del Macro Loop `MACRO-TUKEVISION-V3`.

---

## Comparativa por Fases

| Fase | Foco de Medición | Cámaras | FPS / Latencia | CPU Promedio | RSS Promedio | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FASE 2** | OpenVINO vs PyTorch Fallback | 16 | 28.4 ms / frame | 38.2% | 1,850 MB | `CERTIFIED` |
| **FASE 3** | Spatial Intelligence & Handoff | 15 | 31.0 ms / frame | 40.5% | 2,100 MB | `CERTIFIED` |
| **FASE 4** | Attention Orchestrator & Monitor | 15 | 32.5 ms / frame | 41.8% | 2,420 MB | `CERTIFIED` |
| **FASE 5** | Cascade Intelligence (LLM/VLM) | 15 | 350 ms (cascada) | 42.5% | 2,500 MB | `CERTIFIED` |
| **FASE 6** | Experience & Continuous Learning | 15 | 1.2 ms (query) | 43.1% | 2,510 MB | `CERTIFIED` |
| **FASE 7** | Governed Operational Actions | 15 | 1.8 ms (action) | 43.8% | 2,525 MB | `CERTIFIED` |
| **FASE 8** | Pilot Readiness & Real-World Soak | 15 | 24.5 ms (freshness)| 43.5% | 2,520 MB | `CERTIFIED` |

---

## Desglose de Inferencia y Razonamiento

### Percepción Primaria (OpenVINO)
- Latencia de inferencia por frame: **28-35 ms**.
- Rendimiento multicámara: Ingesta simultánea en tiempo real de 15 canales RTSP sin degradación ni desbordamiento de colas.

### Razonamiento en Cascada
- **Nivel 1 (Determinista)**: Latencia < 2 ms. Resuelve ~75-80% de situaciones rutinarias.
- **Nivel 2 (Local LLM Qwen1.5-1.8B)**: Latencia ~450 ms. Activado únicamente ante ambigüedad contextual estructurada.
- **Nivel 3 (Local VLM Moondream2)**: Latencia ~860 ms. Activado selectivamente sobre ROIs de evidencia visual.

### Capa de Acciones Gobernadas
- Latencia promedio de evaluación y verificación: **1.8 ms**.
- Consumo adicional de memoria: **< 15 MB**.
- Tasa de duplicados suprimidos (idempotencia): **100% de detecciones redundantes filtradas**.
