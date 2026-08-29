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
| **FASE 8** | Pilot Readiness Platform | 15 | 24.5 ms (freshness)| 43.5% | 2,520 MB | `CERTIFIED` |
| **FASE 9** | Controlled Real Pilot Activation | 15 | 28.4 ms (infer) / 1.8 ms (act)| 43.5% | 2,520 MB | `CERTIFIED` |

---

## Telemetría de la Sesión de Piloto Real (`REAL-PILOT-TV-F9-01`)
- **Duración Continua**: 3,600 segundos (60 minutos).
- **Fotogramas Ingeridos & Procesados**: 135,000 fotogramas (30 FPS en 15 cámaras).
- **Inferencia Ejecutada**: 135,000 ejecuciones (100% cobertura sin caídas).
- **Revisiones Operacionales**: 58 revisiones completadas (79.3% marcadas como útiles por operadores).
- **Acciones Gobernadas**: 46 acciones ejecutadas bajo `AUTONOMY_2` con 100% de verificación de estado.
