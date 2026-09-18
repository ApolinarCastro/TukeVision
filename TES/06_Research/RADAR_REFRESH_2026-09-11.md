# Radar refresh — 2026-09-11

## Resultado

Se detectó **un cambio material** para TukeVision: advisory oficial de GeoVision `GV-LPC-2026-09-01`, publicado el 2026-09-10, con 23 CVE sobre GV-LPC2011/2211. La novedad no autoriza incorporar tecnología GeoVision; sí cambia el diseño de seguridad que debe exigirse en Gate 1 LAN/DVR onboarding.

## Hallazgo material — GeoVision GV-LPC2011/2211

**Clasificación TES:** `ADAPTAR / BENCHMARK / WATCH`

**Fuente primaria:** GeoVision Cyber Security / advisory `GV-LPC-2026-09-01`.

**Problema TukeVision que resuelve:** evita diseñar discovery, autenticación y suscripciones ONVIF como si fueran superficies confiables durante onboarding LAN/DVR.

### Patrones materiales verificados

- `CVE-2026-88278`: replay de ONVIF WS-Security UsernameToken/PasswordDigest cuando el dispositivo no exige freshness/nonce reuse protection.
- `CVE-2026-88277`: command injection autenticado a través de datos de ONVIF Subscribe/ConsumerReference.
- `CVE-2026-88287`: DoS remoto no autenticado por manejo no acotado de `Scopes` en WS-Discovery Probe; el registro CVE lista 1.14 como no afectada frente a 1.13.

### Mapeo TukeVision

- Gate 1 LAN/DVR onboarding.
- Inventory de marca/modelo/firmware y capabilities.
- ONVIF discovery y límites de parsing.
- Autenticación/token freshness y replay resistance.
- Sanitización de URI/callback/Subscribe.
- Segmentación de red, least privilege y aislamiento de credenciales.

### Boundary

`VULNERABILITY_IN_ONE_VENDOR != ONVIF_IS_INSECURE`

No se extrapola una vulnerabilidad GeoVision a otros fabricantes. Se adapta únicamente el patrón defensivo vendor-neutral. No se copia código ni se añade dependencia.

### Siguiente gate

Cuando Gate 1 sea autorizado, exigir un `DEVICE_SECURITY_INVENTORY` y pruebas negativas acotadas antes de aceptar un dispositivo como onboarding completo. Si el hardware real es GeoVision, verificar firmware contra el advisory; si no, consultar PSIRT/CVE del fabricante real.

## GitHub — cobertura de forja

- `roryclear/clearcam`: upstream canónico revisado; último commit relevante observado `91f2f77` del 2026-09-08. Sin cambio material posterior que altere la decisión `ACTIVE_EVALUATION_HIGH`.
- `blakeblackshear/frigate`: 0.18 RC2 revisado. Introduce fixes de playback/UI/CUDA y mantiene cambios mayores ya conocidos de 0.18; no cambia el boundary TukeVision ni desplaza ClearCam/Shinobi como candidatos inmediatos para Gate 0C/Gate 1.
- No se incorporaron forks ni mirrors como fuentes.

## GitLab — cobertura de forja

- `Shinobi-Systems/Shinobi`: upstream canónico revisado. No se observó novedad material posterior a la evidencia ya registrada sobre live-grid, next/previous, substreams y auth hardening.
- No se duplicaron forks/mirrors.

## ONVIF / fuentes oficiales

- ONVIF TLS Configuration Add-on 2.0 RC (2026-09-09): sin cambio material posterior; mantiene `BENCHMARK / WATCH / CONTRACT_READINESS`.
- La novedad GeoVision refuerza que Gate 1 debe combinar capability negotiation con controles negativos de seguridad y firmware inventory.

## TES reconciliado

Actualizados:

- `TECHNOLOGY_RADAR.md`
- `KNOWLEDGE_SOURCE_INDEX.md`
- `EXPERIENCE_STORE.md`
- este research note

Revisados y sin cambio:

- `DECISION_LOG.md`: no existe aún decisión de adopción/arquitectura que justifique un ADR nuevo.
- `ACTIVE_EVALUATION_PROTOCOL.md`: ya exige upstream canónico, GitHub+GitLab, licencia/provenance, mapeo, benchmark y condición de reevaluación.

No se modificaron runtime, código, tests, dependencias ni configuración.
