# LOOP-0018N — GATE_MATRIX (PASO 11 pre-check)

Estado de puertas evaluadas hasta PASO 11. (G8+ se completan tras la decisión.)

| Gate | Criterio | Estado | Evidencia |
|---|---|---|---|
| G1 | LOOP no abre nuevo ciclo de estabilización | PASS | Documentos de este LOOP solo PLAN/DISEÑO; ningún cambio de código hasta autorización |
| G2 | Se reutiliza antes de integrar/adaptar | PASS | PRODUCT_CAPABILITY_MATRIX.md: reutiliza RTSPSource/rtsp_url/Pipeline/YOLO/ByteTrack/Zone/Event/Risk/Evidence; E-02/E-04/E-05 REUSABLE_WITH_ADAPTATION (no migrados) |
| G3 | E-02..E-05 100% clasificados | PASS | E02_E05_APPLICABILITY_MATRIX.md: 3 ADAPT + 1 REQUIRES_DECISION (E-03) |
| G4 | Referencias externas mapeadas a gaps reales | PASS | EXTERNAL_REFERENCE_GAP_MATRIX.md: 11 refs; 0 integraciones; 0 dependencias nuevas; Qwen/Face SDK REJECTED |
| G5 | SourceManager decidido | PASS | SOURCEMANAGER_DECISION.md: REQUIRES_SMALL_NEW_ADAPTER (composición) |
| G6 | Prioridad de primera entrega | PASS | FIRST_PRODUCT_DELIVERY.md: REAL_MULTICAMERA_4_CAMERAS |
| G7 | Activity Layer especificado | PASS | ACTIVITY_LAYER_SPEC.md: taxonomía sin THEFT determinista |
| G8 | No duplicar arquitectura | PASS | PRODUCT_CORE.md: especialización multicámara de ARCHITECTURE.md |
| G9 | Escalado 1→4 (8/16 prohibido) | PASS | SOURCEMANAGER_DECISION.md + FIRST_PRODUCT_DELIVERY.md: solo 4 |
| G10 | Política AI | PASS | AI_POLICY.md: determinista + razonamiento opcional + UNKNOWN válido |
| G11 | Presupuesto de recursos | PASS | resource_budget.md: YOLO 54.5ms → frame budgeting; ECONOMY/BALANCED/QUALITY; GPU futuro |
| G12 | SIN dependencias nuevas | PASS | NINGUNA referencia exige nueva lib; SourceManager usa stdlib + piezas existentes |
| G13 | SIN migración automática E-xx | PASS | Regla de activación en E02_E05_APPLICABILITY_MATRIX.md |
| G14 | SIN tocar E-01/OpenCV/FFmpeg | PASS (garantía de diseño) | SourceManager compone; no modifica live_sources.py/rtsp_url.py |
| G15 | SIN fuentes 8/16 tras 4 | PASS | Explícito en FIRST_PRODUCT_DELIVERY.md |
| G16 | Aislamiento por cámara | PASS (diseño) | PRODUCT_CORE.md invariante: SOURCE_ISOLATION=YES, NO_SHARED_MUTABLE_CAPTURE=YES |
| G17 | STOP final con revisión humana | PENDIENTE | Al final del LOOP |

## PASO 11 — DECISIÓN DE PUERTA (PENDIENTE DE AUTORIZACIÓN)

**Lo que dice el LOOP:** "NO SourceManager/Activity Layer sin autorización" + STOP final con revisión humana.

**Lo que la evidencia permite:**
- El plan está completo y todas las puertas de diseño (G1-G16) se cumplen.
- La implementación mínima (SourceManager ~1 archivo, composición de piezas certificadas,
  0 deps nuevas, 0 toques a E-01) es viable y auditable.
- Hallazgo de recursos: YOLO 54.5ms/frame → la detección por cámara debe ser config-driven
  con frame budgeting; el SourceManager (orquestación) NO depende de YOLO continuo.

**Decisión requerida del operador:** autorizar la implementación mínima de
REAL_MULTICAMERA_4_CAMERAS (branch `product/loop-0018n-multicamera4`) o detener el LOOP
en plan (veredicto PRODUCT_ADVANCE_PLAN_READY sin código).