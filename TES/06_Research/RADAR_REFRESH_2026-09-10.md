# Radar Refresh — 2026-09-10

## Scope

Revisión material del ecosistema CCTV/ONVIF con GitHub y GitLab como forjas de primera clase, contrastada contra `TECHNOLOGY_RADAR.md`, `EXPERIENCE_STORE.md`, `KNOWLEDGE_SOURCE_INDEX.md`, `DECISION_LOG.md` y `ACTIVE_EVALUATION_PROTOCOL.md`.

## Resultado ejecutivo

Se detectaron dos novedades materiales que justifican actualización TES documental:

1. **ONVIF TLS Configuration Add-on 2.0 Release Candidate** — publicada por ONVIF el 2026-09-09.
2. **Shinobi upstream GitLab** — cambios recientes de live-grid, substream, next/previous navigation y hardening de seguridad que mapean directamente a Gate 0C y Gate 1.

No se modifica runtime, código, tests, dependencias ni configuración.

---

## Hallazgo 1 — ONVIF TLS Configuration Add-on 2.0 RC

**Clasificación TES:** `BENCHMARK / WATCH / CONTRACT_READINESS`

- **Upstream canónico:** ONVIF.
- **Fuente primaria:** anuncio oficial ONVIF del 2026-09-09.
- **Repositorio de desarrollo:** `https://github.com/onvif/specs`.
- **Release pública de specs verificada:** `26.06` (`68ee1b5`, publicada 2026-07-02); la RC TLS 2.0 fue anunciada después y ONVIF prevé finalización a fin de 2026.
- **Licencia del repositorio de specs:** especificaciones bajo licencia ONVIF no-derivatives; contribuciones bajo Apache según el repositorio.
- **Cambio material:** endurecimiento de métodos TLS/configuración interoperable y separación de requisitos de seguridad en add-ons versionables.
- **Problema TukeVision:** Gate 1 LAN/DVR onboarding no debe asumir transporte/configuración segura sin capability discovery real.
- **Mapeo:** ONVIF discovery/configuration, credential transport, device capabilities, DVR onboarding, security posture.
- **Riesgo:** Release Candidate != estándar final; soporte del DVR/cámara debe comprobarse físicamente.
- **Siguiente gate:** inventario de capacidades TLS/ONVIF durante Gate 1; sandbox sólo donde el hardware exponga la función. Reevaluar con versión final/test tools.

**No integración directa ahora.**

---

## Hallazgo 2 — Shinobi (GitLab upstream)

**Clasificación TES:** `BENCHMARK / ADAPTAR PATRONES`

- **Forge:** GitLab.
- **Upstream canónico:** `https://gitlab.com/Shinobi-Systems/Shinobi`.
- **Mirror/fork:** no se usa ninguno como autoridad.
- **Actividad reciente verificada:** commit `c4cb68d0`, 2026-08-20, `Fix Sub Account Live Grid render`.
- **MR !548:** incluye fixes de `open next/previous monitor navigation`, `loading substream issues`, auto-open/autosizing y opciones ONVIF/RTSP.
- **MR !557 (2026-08-05):** hardening de authentication/permissions, pairing/debug routes y file-write containment.
- **Licencia:** Shinobi Open Source Software License Agreement (EULA propia con condiciones comerciales). `DIRECT_CODE_REUSE=NO`.
- **Problema TukeVision:** Gate 0C mostró exactamente regressions de grid, navegación focus anterior/siguiente y transición de substream; Gate 1 incorporará onboarding LAN/DVR.
- **Mapeo:** UI lifecycle, live-grid ownership, focus navigation, SUB/MAIN transition, ONVIF scanner, RTSP transport, onboarding security.
- **Riesgo:** Shinobi es un NVR/VMS completo y su licencia no es una dependencia adecuada para el core TukeVision.
- **Siguiente gate:** benchmark de comportamiento/patrón desde el baseline estable antes de rediseñar Gate 0C; revisar patrones de seguridad de onboarding en Gate 1.

**No integrar Shinobi como producto/dependencia.**

---

## GitHub coverage

Se revisaron fuentes oficiales/primarias y upstreams relevantes en GitHub, incluyendo:

- `onvif/specs` — upstream de desarrollo de especificaciones ONVIF.
- `onvif/media-signing-framework` — permanece `ACTIVE_EVALUATION / CONTRACT_READY`; no se detectó un cambio que altere la decisión TES vigente.
- candidatos CCTV/NVR recientes — sin evidencia suficiente para desplazar los benchmarks ya priorizados (ClearCam, Frigate, Shinobi).

`ONVIF Media Signing` se mantiene sin cambio de clasificación: sigue siendo Release Candidate/benchmark de provenance, ya representado en TES.

## GitLab coverage

GitLab fue revisado explícitamente, no tratado como forge secundaria.

`Shinobi-Systems/Shinobi` resultó materialmente relevante y se incorpora como un único `SOURCE_ID` por ser el upstream canónico. No se duplica `ShinobiCE`, mirrors ni forks.

---

## Reconciliación TES

### TECHNOLOGY_RADAR.md

Actualizar con:

- ONVIF TLS Configuration Add-on 2.0 RC: `BENCHMARK / WATCH / CONTRACT_READINESS`.
- Shinobi: `BENCHMARK / ADAPTAR`, patrón sólo; no dependencia.

### EXPERIENCE_STORE.md

Añadir:

- `EXP-ONVIF-TLS-001`.
- `EXP-SHINOBI-001`.

### KNOWLEDGE_SOURCE_INDEX.md

Añadir:

- `ONVIF-TLS-CONFIG-2`.
- `SHINOBI-GITLAB`.

### DECISION_LOG.md

**Sin cambio.** Ningún hallazgo autoriza una nueva adopción arquitectónica: ambos permanecen en benchmark/watch/contract-readiness. No se crea ADR hasta que un gate decida incorporar una capacidad o cambiar una frontera.

### ACTIVE_EVALUATION_PROTOCOL.md

**Sin cambio.** El protocolo vigente ya exige GitHub+GitLab, upstream canónico, licencia, actividad, mapeo y reevaluación. La ejecución de este refresh demuestra ese protocolo; no requiere modificación normativa.

---

## Gate recommendation

1. **Gate 0C:** antes de nuevo código, benchmark documental/arquitectónico de los patrones Shinobi para live-grid + next/previous + substream, comparados con ClearCam/Frigate y el baseline estable TukeVision.
2. **Gate 1:** añadir a la checklist de onboarding DVR un inventario de capacidades ONVIF/TLS, sin requerir ni declarar TLS Add-on 2.0 si el hardware no lo soporta.
3. **Reevaluación ONVIF TLS 2.0:** versión final/test tools a fin de 2026, o antes si hardware real soporta configuración TLS.
