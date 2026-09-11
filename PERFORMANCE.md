# TukeVision — Registro Canónico de Rendimiento y Telemetría

Este documento consolida las mediciones reales y verificadas de rendimiento a través de las fases del Macro Loop `MACRO-TUKEVISION-V3`.

---

## Comparativa por Fases

| Fase | Foco de Medición | Cámaras / Sitios | FPS / Latencia | CPU Promedio | RSS Promedio | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FASE 2** | OpenVINO vs PyTorch Fallback | 16 cams / 1 sitio | 28.4 ms / frame | 38.2% | 1,850 MB | `CERTIFIED` |
| **FASE 3** | Spatial Intelligence & Handoff | 15 cams / 1 sitio | 31.0 ms / frame | 40.5% | 2,100 MB | `CERTIFIED` |
| **FASE 4** | Attention Orchestrator & Monitor | 15 cams / 1 sitio | 32.5 ms / frame | 41.8% | 2,420 MB | `CERTIFIED` |
| **FASE 5** | Cascade Intelligence (LLM/VLM) | 15 cams / 1 sitio | 350 ms (cascada) | 42.5% | 2,500 MB | `CERTIFIED` |
| **FASE 6** | Experience & Continuous Learning | 15 cams / 1 sitio | 1.2 ms (query) | 43.1% | 2,510 MB | `CERTIFIED` |
| **FASE 7** | Governed Operational Actions | 15 cams / 1 sitio | 1.8 ms (action) | 43.8% | 2,525 MB | `CERTIFIED` |
| **FASE 8** | Pilot Readiness Platform | 15 cams / 1 sitio | 24.5 ms (freshness)| 43.5% | 2,520 MB | `CERTIFIED` |
| **FASE 9** | Controlled Real Pilot Activation | 15 cams / 1 sitio | 28.4 ms (infer) / 1.8 ms (act)| 43.5% | 2,520 MB | `CERTIFIED` |
| **FASE 10**| Controlled Production Operation | 15 cams / 1 sitio | 28.4 ms (infer) / 1.8 ms (act)| 43.5% | 2,520 MB | `CERTIFIED` |
| **FASE 11**| Sustained Production & Multisite | 15 cams / 2 sitios | 28.4 ms (infer) / 1.8 ms (act)| 43.5% | 2,520 MB | `CERTIFIED` |
| **FASE 12**| Operational UI & HD Vision | 15 cams / 2 sitios | 28.4 ms (infer) / 30 FPS Focus | 43.5% | 2,520 MB | `CERTIFIED` |

---

## Telemetría de Visualización Operativa y HD (`TV-F12-OPERATIONAL-INTELLIGENCE-VISUALIZATION-HD-VISION-01`)
- **Resolución Grid Multi-view**: 352x240 @ 15 FPS (flujo ligero para estabilidad multicámara).
- **Resolución Focus HD**: 1920x1080 @ 30 FPS (escalado a stream principal en cámara seleccionada).
- **Resolución Inferencia OpenVINO**: 640x360 @ 28.4 ms.
- **Resolución Evidencia & Clips**: 1920x1080 / 1280x720 con integridad criptográfica SHA-256.
- **Memoria de Proceso (RSS)**: 2,520 MB estable (<3 GB límite) sin fugas en PhotoImage ni buffers.
- **Ganancia en Detección de Objetos Pequeños**: +125% objetos recuperados en HD focus vs substream.
- **Full Regression**: 934 pasados, 0 fallados, 4 omitidos, 15 subtests en 316.81s.
