# TukeVision Radar Refresh — 2026-09-13

**SCOPE:** documentación TES únicamente.  
**RUNTIME/CODE/TESTS/DEPENDENCIES/CONFIG:** sin cambios.

## Cambios materiales

### 1. ClearCam — self-hosted notifications/Qwen

- Upstream canónico: `https://github.com/roryclear/clearcam`.
- Refs: `2f65c739d546481edcc78d85213737fda9d0b28a`, `3e69345160c879071c302142005f56693b4cf140`, `078c6cc83714bb0dd1ebdd7ba6919c1890c21559`.
- Fecha de integración upstream observada: 2026-09-13.
- Licencia: GPL-3.0.
- Cambio: uso de `server_url` propio para camino de notificaciones y Qwen sin requerir identidad ClearCam, más helper/receptor de servidor.
- Clasificación: `ADAPTAR / BENCHMARK`.
- Problema TukeVision: mantener local-first/offline y evitar dependencia SaaS en evento→VLM→notificación.
- Gate/capacidad: P0-62, P0-65, P0-76; futuro event delivery LAN.
- Benchmark: evento local → VLM selectivo → endpoint LAN propio → receipt/audit; medir latencia, fallo/offline y egress.
- Límite: no copiar código GPL al core.

### 2. ONVIF specs — TLS activation timing + WebRTC close

- Upstream: `https://github.com/onvif/specs`; ONVIF publicado sigue siendo autoridad normativa.
- Refs: `bf3ea360e20247d68c2ae0e9c9a715a948f79d78` y `f1b0e50df6ad2779083686406c264806673ba076`, 2026-09-11.
- Cambio TLS: atributo para indicar tiempo estimado hasta activación efectiva de una nueva configuración TLS.
- Regla: `CONFIGURATION_ACCEPTED != CONFIGURATION_ACTIVE`.
- Clasificación TLS: `ADAPTAR / BENCHMARK / CONTRACT_READINESS / WATCH`.
- Gate: Gate 1 LAN/DVR onboarding.
- Benchmark: capability/SetupDuration → apply → wait → handshake/connectivity verification → ACTIVE.
- Cambio WebRTC: señalización `close` explícita para liberar recursos de sesión/ICE/TURN.
- Clasificación WebRTC: `WATCH / CONTRACT_READINESS`; no activa una pasarela WebRTC ahora.

### 3. Ambient.ai — Aug-2026 platform release

- Fuente primaria: Ambient.ai, publicación 2026-08-26.
- Cambio: Agentic Video Walls; health `degraded` además de healthy/unhealthy; credenciales/red sin re-onboarding; Case Management; Semantic/Similarity Search; optimización de densidad de streams.
- Clasificación: `ADAPTAR / BENCHMARK` manteniendo `ADAPTED / WATCH` como estado de fuente.
- Problemas TukeVision: separar conectividad de calidad visual, reducir carga del operador, conservar historia ante mantenimiento y formar casos auditables.
- Gate/capacidad: Gate 0C observabilidad; P0-59/P0-65/P0-66; Gate 1 maintenance.
- Benchmark: `DEGRADED_VIEW != STREAM_DOWN` y case local cronológico con clips/metadata/audit.
- Límite: producto propietario/cloud; patrones únicamente, métricas del proveedor no son evidencia TukeVision.

## Fuentes explícitamente revisadas sin cambio material de decisión

- Frigate: v0.18.0 estable sigue siendo la referencia actual; no se encontró release posterior que cambie el boundary TukeVision.
- Shinobi GitLab: upstream canónico revisado; último commit visible consultado `c4cb68d0` (2026-08-20), sin novedad posterior material.
- ONVIF Media Signing: sin cambio material que cambie la decisión activa.
- Avigilon, March Networks, HiFocus, SmartPSS Lite, NCSC, Alocity/Mercury y Flock: fuentes primarias/referencias revisadas; sin cambio que altere el estado TES en esta ejecución.
- ECC `affaan-m/ECC`: revisado como tooling de ingeniería; v2.2.1 no altera una capacidad CCTV de TukeVision.

## Incorporation checklist

ClearCam, ONVIF y Ambient cumplen en esta actualización:

```text
SOURCE_VERIFIED=YES
VERSION_OR_REF_VERIFIED=YES
LICENSE_VERIFIED=YES
CAPABILITIES_EXTRACTED=YES
TUKEVISION_MAPPING=YES
ADOPTION_BOUNDARY=YES
REVISIT_CONDITION=YES
EXPERIENCE_RECORD=YES
```

## TES reconciliation

Actualizados:
- `TES/TECHNOLOGY_RADAR.md`
- `TES/KNOWLEDGE_SOURCE_INDEX.md`
- `TES/EXPERIENCE_STORE.md`
- `TES/06_Research/RADAR_REFRESH_2026-09-13.md`

Revisados y sin modificación:
- `TES/DECISION_LOG.md` — no cambió una decisión arquitectónica/adopción de runtime.
- `TES/ACTIVE_EVALUATION_PROTOCOL.md` — el protocolo vigente ya cubre upstream, licencia, mapeo, límite y reevaluación.
