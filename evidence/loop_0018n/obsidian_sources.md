# LOOP-0018N — OBSIDIAN SOURCES (PASO 1)

Fuentes canónicas localizadas en `C:\Users\ASUS Zenbook\Documents\TukeVision\TES`
y utilizadas para construir este plan (sin duplicar arquitectura).

## Vault / Dashboard
- `00_Dashboard/PROJECT_STATUS.md` — estado oficial + LOOP-0018M/0018M-R1 (E-01 CLOSED, checkpoint `ccacb3d`).
- `00_Dashboard/Nuestras reglas.md` — reglas de gobierno (regla 22: no nueva herramienta sin necesidad aprobada).

## Vision / Product
- `01_Vision/VISION.md` — (gap documental, 0 bytes).
- `02_Product/PRODUCT.md` — (gap documental, 0 bytes).
- `02_Product/OBSERVABLES.md` — observables del producto.

## Architecture
- `03_Architecture/ARCHITECTURE.md` — pipeline canónico (Fuente→Captura→Detección→Tracking→Obs→Evento→Negocio→Riesgo→Alerta→Evidencia→Revisión humana→Incidente).
- `03_Architecture/TECHNOLOGY_STACK_MVP.md` — stack activo; regla de incorporación.
- `03_Architecture/TECHNOLOGY_MAP.md` — mapa capa→tecnología.
- `03_Architecture/EVENTS.md`, `OBSERVATION.md`, `SYSTEM_BRAIN.md`, `PRODUCT_RULES.md`.

## Business / Concept
- `03_Business/MAPA_CONCEPTUAL.md`, `Camara.md`, `Zona.md`, `Producto.md`, `Evento.md`, `Riesgo.md`, `Evidencia.md`, `Observacion.md`, `Incidente.md`, `Alerta.md`, `Tienda.md`, `Persona.md`.

## Decisions
- `04_Decisions/DECISIONS.md` (índice, hasta DEC-0032).
- `DEC-0013` (no identifica personas), `DEC-0015` (cámara es fuente), `DEC-0005/0006` (observación/evento), `DEC-0007` (evidencia inmutable), `DEC-0008` (reglas del negocio), `DEC-0009` (riesgo dinámico), `DEC-0010` (alerta excepción), `DEC-0011/0012` (revisión humana), `DEC-0023` (stack MVP), `DEC-0028/0029` (registro tecnológico), `DEC-0031` (portable), `DEC-0032` (E-01).

## Specs / Research / Backlog
- `05_Specs/SPEC-0001` (primer prototipo certificado), `SPEC_INDEX.md`.
- `06_Research/NVIDIA - Context Aware Video AI.md` (DeepStream, multi-cámara, GPU → trigger).
- `06_Research/Fuentes de observación.md`, `Arquitectura Multi-Tienda.md`, `PRIORIZACION_CASOS_NICOPOLY.md`, `Pendientes de Arquitectura.md`, `UC001_OPERATIONAL_INPUT.md`.
- `07_Backlog/BACKLOG.md` (E-01 CLOSED; E-02..E-05 PENDING), `NICOPOLY_USE_CASES.md`.
- `08_Journal/DEVELOPMENT_LOG.md` (hasta LOOP-0018M-R1).

## Resources
- `09_Resources/TECHNOLOGY_AND_REFERENCE_REGISTRY.md` (registro maestro; OpenCV/YOLO/ByteTrack/Supervision/trackers ACTIVE; FFmpeg UNKNOWN; DeepStream/Qwen/n8n REJECTED/FUTURE).
- `09_Resources/TECHNOLOGY_MAP.md`, `RESOURCE_INDEX.md`, `DEVELOPMENT_TOOLING.md`.

## Portable evidence (laboratorio)
- `LOOP-0018F-SMARTPSS-B1-DISCRIMINANT.md` (B1 INCONCLUSIVE; 0xc0000374 histórico).
- `LOOP-0018C-R1-PHYSICAL-RECERTIFICATION.md` (STABLE_STREAM_NOT_CERTIFIED pre-fix).
- `LOOP-0018L-PHYSICAL-RTSP-LIFECYCLE-RECERTIFICATION.md` (CAM07 3774s clean; reconnect NOT_EXERCISED).
- `evidence/loop_0018j/certified_change_map.md` (E-01..E-05 clasificados EXPERIMENTAL).
- `evidence/loop_0018j_r4/experimental_e01_e05_map.md` (archivos por E-xx).
- `evidence/loop_0018j_r4/folder_disposition_matrix.md`.

G8 (NO_DUPLICATE_ARCHITECTURE) → la arquitectura canónica (ARCHITECTURE.md flujo) NO se reemplaza; este loop formaliza el Core Product como especialización multicámara coherente con ella.