# TukeVision — Failure Library

## FAIL-TV-GATE0C-PHYSICAL-001

- **DATE:** 2026-09-28
- **EXECUTION_ID:** `TV-GATE0C-PHYSICAL-VERIFY-001`
- **STATE:** `CLOSED_AS_HARNESS_FAILURE`
- **EXECUTION_RESULT:** `FAIL`
- **PRODUCT_GATE_RESULT:** `NOT_TESTED`
- **FIRST_FAILURE:** `POWERSHELL_SYNTAX_ERROR_NULL_COALESCING_UNSUPPORTED`
- **ENVIRONMENT:** Windows PowerShell 5.1
- **OBSERVED:** la instrucción de verificación contenía el operador null-coalescing `??`, disponible en PowerShell 7+ pero no en Windows PowerShell 5.1. El parser falló antes de ejecutar la verificación física.
- **PRODUCT_RUNTIME_EXERCISED:** `NO`
- **MONITOR_DURATION_SECONDS:** `0`
- **MONITOR_VALID_SAMPLES:** `0`
- **STATIC_GATE0C_PRECONDITION:** `PASS (27/27 targeted tests)`
- **IMPACT:** no existe evidencia física nueva a favor ni en contra de Gate 0C. No cambiar `PHYSICAL_GATE0C` a FAIL por este evento.
- **CORRECTIVE_RULE:** las instrucciones Antigravity para este host deben usar sintaxis compatible con Windows PowerShell 5.1 salvo que el runtime verifique explícitamente PowerShell 7.
- **RETRY_POLICY:** sólo una nueva ejecución con nuevo Execution ID; nunca reinterpretar la ejecución fallida como PASS.
- **NEXT_TASK:** `TV-GATE0C-PHYSICAL-VERIFY-002`
- **PRODUCT_CODE_CHANGED:** `NO`
- **TESTS_CHANGED:** `NO`


## FAIL-TV-GATE0C-PHYSICAL-002

- **DATE:** 2026-09-28
- **EXECUTION_ID:** `TV-GATE0C-PHYSICAL-VERIFY-002`
- **STATE:** `CLOSED_AS_HARNESS_FAILURE`
- **EXECUTION_RESULT:** `FAIL`
- **PRODUCT_GATE_RESULT:** `NOT_TESTED`
- **FIRST_FAILURE:** `INSUFFICIENT_PHYSICAL_OBSERVATION`
- **ENVIRONMENT:** Windows PowerShell 5.1 under Antigravity command-session orchestration
- **OBSERVED:** el runtime real fue localizado como `RUN-870246`, PID `15088`, con 15 cámaras; después de iniciar un monitor mediante `Start-Job`, la sesión de PowerShell terminó y el job no sobrevivió para producir la ventana de 600 s. La confirmación del operador quedó vacía.
- **MONITOR_DURATION_SECONDS:** `0`
- **MONITOR_VALID_SAMPLES:** `0`
- **MONITOR_ERRORS:** `0`
- **SOURCE_CLOSED_COUNT:** `25`
- **SOURCE_RETRY_COUNT:** `18`
- **CRITICAL_FILE_HASH_DELTA:** `EMPTY`
- **VERIFY_CODE_INTEGRITY:** `PASS`
- **STATIC_GATE0C_PRECONDITION:** `PASS (27/27 targeted tests)`
- **IMPACT:** no hay evidencia física suficiente para evaluar Grid/Focus/Zoom/PrevNext/SWITCHING_PROFILE/health accounting. Los campos UI marcados FAIL derivan de confirmación vacía y no son prueba de fallo del producto.
- **UPSTREAM_RTSP_TRIGGER_PROVEN:** `NO`
- **CORRECTIVE_RULE:** no usar `Start-Job` para observaciones que deban sobrevivir a una sesión de comando de Antigravity. El monitor debe ejecutarse en un proceso PowerShell independiente y persistente, con archivo externo al repo y handoff explícito entre start/collect.
- **NEXT_TASK:** `TV-GATE0C-PHYSICAL-VERIFY-003A`
- **PRODUCT_CODE_CHANGED:** `NO`
- **TESTS_CHANGED:** `NO`


## FAIL-TV-GATE0C-PHYSICAL-003A

- **DATE:** 2026-10-02
- **EXECUTION_ID:** `TV-GATE0C-PHYSICAL-VERIFY-003A`
- **STATE:** `CLOSED_AS_PRECONDITION_FAILURE`
- **EXECUTION_RESULT:** `FAIL`
- **PRODUCT_GATE_RESULT:** `NOT_TESTED`
- **FIRST_FAILURE:** `ACTIVE_RUNTIME_NOT_FOUND`
- **OBSERVED:** no active Python runtime could be matched to any current `evidence/RUN-*/identity.json`; `ACTIVE_RUNTIME_CANDIDATES=0`.
- **RUNTIME_ID:** `NONE`
- **CAMERA_COUNT:** `UNKNOWN`
- **TELEMETRY_BASELINE_CAPTURED:** `NO`
- **PRODUCT_RUNTIME_EXERCISED:** `NO`
- **STATIC_GATE0C_PRECONDITION:** `PASS (27/27 targeted tests)`
- **IMPACT:** no physical product conclusion is possible. Keep `PHYSICAL_GATE0C=NOT_TESTED`.
- **CORRECTIVE_RULE:** do not run physical Gate 0C baseline/interaction loops until a separate runtime-ready precheck proves exactly one active TukeVision runtime with 15 configured cameras and advancing native telemetry.
- **NEXT_TASK:** `TV-GATE0C-RUNTIME-READY-001`
- **PRODUCT_CODE_CHANGED:** `NO`
- **TESTS_CHANGED:** `NO`


## FAIL-TV-GATE0C-PHYSICAL-003C

- **DATE:** 2026-10-02
- **EXECUTION_ID:** `TV-GATE0C-PHYSICAL-VERIFY-003C`
- **STATE:** `OPEN_ROOT_CAUSE_ANALYSIS`
- **EXECUTION_RESULT:** `FAIL`
- **PRODUCT_GATE_RESULT:** `FAIL`
- **FIRST_REPORTED_FAILURE:** `F12_HEALTHY_LIVE_MISMATCH`
- **RUN:** `RUN-8EF244`, PID `22764`
- **OBSERVATION:** 480 s / 443 valid samples; acceptance required >=600 s.
- **HEALTH_ACCOUNTING:** 0 failures; SWITCHING_PROFILE exercised; frame/UI sequences advanced.
- **F12_OBSERVATION:** final snapshot contained 2 cameras with `capture_state=HEALTHY` while `live != true` or `liveness_state != ONLINE`.
- **F12_LIMITATION:** no per-camera `frame_age_s` or reader-heartbeat age was recorded in the report, so this does not yet distinguish a TrueLiveness defect from valid stale-frame handling.
- **OPERATOR_CONFIRMATION:** missing; UI Grid/Focus/Zoom/PrevNext results are `NOT_OBSERVED`, not evidence-backed FAILs.
- **SOURCE_CLOSED:** 31 -> 72 (delta 41).
- **SOURCE_RETRY:** 28 -> 65 (delta 37).
- **UPSTREAM_RTSP_TRIGGER_PROVEN:** `NO`; counts alone do not prove cause.
- **CODE_INTEGRITY:** critical hashes unchanged.
- **NEXT_TASK:** `TV-GATE0C-F12-DIAG-001`.
- **RULE:** diagnose before patch; no re-run-to-PASS and no implementation until root cause is classified.
