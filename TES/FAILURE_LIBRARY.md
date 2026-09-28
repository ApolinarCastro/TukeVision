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
