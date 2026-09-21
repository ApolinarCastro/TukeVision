# Radar Refresh — 2026-09-21 — Frigate DEEPX NPU

## Resultado

Cambio material verificado en `blakeblackshear/frigate`.

- **SOURCE_VERIFIED:** YES — upstream canónico `blakeblackshear/frigate`.
- **VERSION_OR_REF_VERIFIED:** commit `af0ba191966812cf9ac8515d95b1dd221363d17e`, 2026-09-21.
- **LICENSE_VERIFIED:** MIT (`LICENSE` del mismo ref).
- **CAPABILITIES_EXTRACTED:** detector/runtime DEEPX NPU; soporte SSD, DAMO-YOLO, YOLO genérico/YOLOX; PPU/anchor-free decoding; score/NMS configurables; validación de modelo/driver; datos de latencia actualizados.
- **TUKEVISION_MAPPING:** hardware acceleration / detector portability / future non-Intel edge profile. El perfil actual conserva OpenVINO como runtime primario.
- **ADOPTION_BOUNDARY:** no integrar Frigate ni su runtime; no convertir TukeVision en segundo NVR; extraer sólo el patrón de abstracción de acelerador y benchmark de hardware cuando exista hardware DEEPX real.
- **REVISIT_CONDITION:** disponibilidad real de DEEPX en un perfil TukeVision o evidencia de que OpenVINO no cubre el hardware objetivo.
- **EXPERIENCE_RECORD:** `EXP-FRIGATE-DEEPX-001` en este refresh y fuente dedicada `TES/09_Resources/Sources/GitHub/FRIGATE-DEEPX-2026-09-21.md`.

## Clasificación

`BENCHMARK | RESERVE`

No cambia la decisión arquitectónica actual: OpenVINO sigue adoptado para el perfil Intel vigente. DEEPX amplía la evidencia de que la capa de detección debe conservar una frontera de acelerador neutral, pero no justifica una nueva dependencia ni un cambio de runtime sin hardware y benchmark propios.

## Problema TukeVision afectado

Portabilidad futura de inferencia edge y riesgo de acoplar el detector a un único backend/hardware.

## Gate / capacidad

Hardware acceleration / detector abstraction / future edge profile. No abre un gate nuevo y no altera el baseline certificado.

## Riesgos

- Añadir soporte sin hardware real produciría complejidad no validada.
- Los datos de latencia upstream no son evidencia de rendimiento TukeVision.
- Integrar Frigate violaría el límite de producto; sólo se estudia el patrón.

## Benchmark mínimo

Sólo cuando exista hardware DEEPX objetivo: mismo modelo/dataset y mismo workload real contra el backend vigente; medir precisión, p50/p95 de inferencia, FPS sostenido, CPU/RAM, consumo del acelerador, estabilidad >=1800 s, recovery y degradación ante fallo del runtime. Cero cambio de Evidence First y cero media egress.

## Siguiente gate

`RESERVE` hasta que exista hardware DEEPX real o una brecha demostrada del backend actual. Entonces ejecutar benchmark aislado antes de cualquier decisión de integración.

## EXP-FRIGATE-DEEPX-001

- **PROBLEM:** futura portabilidad de inferencia edge sin acoplar TukeVision a un NVR o backend único.
- **PATTERN:** detector abstraction + hardware-specific runtime behind a stable boundary + explicit model/driver validation.
- **SOURCE:** `blakeblackshear/frigate@af0ba191966812cf9ac8515d95b1dd221363d17e`.
- **DECISION:** `BENCHMARK / RESERVE`.
- **BOUNDARY:** Frigate no se integra; DVR/NVR sigue siendo grabador primario; OpenVINO no se reemplaza sin benchmark reproducible.
- **REVISIT_WHEN:** hardware DEEPX objetivo disponible o brecha real de OpenVINO demostrada.

## Fuentes obligatorias revisadas

La cola canónica TES fue consultada antes de evaluar el cambio. En esta ejecución no se observó otro cambio verificado que altere materialmente una clasificación o decisión vigente en ClearCam, ECC, ONVIF Media Signing/specs, Qwen-MM-Plugins, MiniCPM/MiniCPM-V, OpenViewer o Shinobi. La ausencia de cambio material no genera escritura adicional.