# Radar/TES Refresh — 2026-09-14

## Resultado material

Se detectó una brecha de reconciliación en una fuente ya activa: **March Networks** estaba registrada en TES sólo como referencia enterprise genérica, pero su release oficial **2026 Mid-Year Release** del 2026-08-11 contiene dos patrones directamente aplicables a capacidades abiertas de TukeVision.

## Fuente verificada

- `SOURCE_ID=MARCH-NETWORKS`
- `CANONICAL_UPSTREAM=https://www.marchnetworks.com/`
- `PRIMARY_RELEASE=2026 Mid-Year Release`
- `RELEASE_DATE=2026-08-11`
- `LICENSE=PROPRIETARY_PRODUCT_REFERENCE`
- `SOURCE_VERIFIED=YES`
- `VERSION_OR_REF_VERIFIED=YES`
- `LICENSE_VERIFIED=YES`
- `CAPABILITIES_EXTRACTED=YES`
- `TUKEVISION_MAPPING=YES`
- `ADOPTION_BOUNDARY=YES`
- `REVISIT_CONDITION=YES`
- `EXPERIENCE_RECORD=EXP-MARCH-001`

## Cambio material

La release oficial documenta:

1. **AI Smart Search** sobre snapshots capturados a intervalos configurables, con búsqueda por lenguaje natural e imagen y retorno a la evidencia/video relacionado.
2. Búsqueda expandida de rostro y matrícula sobre dispositivos compatibles.
3. Integración **C•CURE access control → video** para investigar eventos de acceso junto con el video asociado.
4. Searchlight AI para análisis bajo demanda de datos operacionales vinculados al video.
5. Ampliación de integración con cámaras/plataformas VIVOTEK.

## Problemas TukeVision relacionados

- `P0-65`: investigación histórica sin procesar de forma continua cada frame.
- Correlación `ACCESS_EVENT + VIDEO + LOCATION + TIME` manteniendo `CREDENTIAL_EVENT != PERSON_IDENTITY`.
- Evidence First: un resultado de búsqueda debe poder volver al clip/frame/origen verificable.
- Multisitio/agregador: normalizar señales y luego correlacionar, no adoptar un VMS vertical.

## Clasificación

`BENCHMARK / ADAPTAR`

Estado anterior: `ACTIVE_EVALUATION` genérico.

Estado recomendado: `BENCHMARK / ACTIVE_EVALUATION` con patrón concreto `REPRESENTATIVE_SNAPSHOTS -> SEARCHABLE_INDEX -> QUERY -> CANDIDATE_RESULT -> SOURCE_VIDEO/EVIDENCE`.

No se eleva a `ACTIVE_ENGINEERING_CANDIDATE`: March Networks es un producto propietario/cloud-capable y la utilidad para TukeVision está en los patrones, no en integrar el producto.

## Boundary de adopción

- `SECOND_NVR=NO`
- `DVR_NVR_PRIMARY_RECORDER=YES`
- `LOCAL_FIRST=YES`
- `CLOUD_DEPENDENCY=NO`
- `DIRECT_CODE_REUSE=NO`
- `AI_RESULT_IS_LEAD_NOT_FACT=YES`
- `ZERO_FABRICATED_EVIDENCE=YES`

## Benchmark mínimo decisivo

### Historical search

Mismo histórico local/DVR:

- estrategia A: snapshots representativos a intervalos configurables + índice local;
- estrategia B: análisis continuo equivalente.

Medir:

- recall útil sobre consultas definidas;
- latencia de búsqueda;
- CPU/RAM;
- volumen indexado;
- trazabilidad exacta del resultado al clip/frame fuente.

### Access correlation

`ACCESS_EVENT -> RELATED_VIDEO -> HUMAN_VALIDATION`

Validar que:

- la credencial no se convierta en identidad visual;
- el evento preserve source/time/location;
- el video relacionado sea evidencia real, no reconstrucción/inferencia;
- el caso quede auditable.

## Siguiente gate

Ejecutar este benchmark sólo cuando se active el slice P0-65 o el conector ACCESS/correlación. No habilita implementación anticipada.

## Frescura verificada en paralelo

- **ClearCam:** `main@f92e3cba` (2026-09-14) sólo amplía README con Home Assistant/Pushover/N8N/custom URL para la capacidad de notificaciones ya registrada; no cambia la decisión TES.
- **Frigate:** `main` activo el 2026-09-14; cambios recientes de Hailo/dependencias no alteran el benchmark Gate 0C/Gate 1 ni existe release posterior material a 0.18.0 en esta pasada.
- **ECC `affaan-m/ECC`:** release visible `v2.2.1`; actividad reciente de memory/control-plane sin capacidad CCTV material nueva.
- **ONVIF:** `onvif/specs` sin commit posterior al conjunto material del 2026-09-11 para TLS/WebRTC/security.
- **GitLab Shinobi:** upstream canónico revisado; no se detectó cambio material posterior a la evidencia `c4cb68d0` relevante para Gate 0C/Gate 1.

## Documentos TES modificados

- `TES/TECHNOLOGY_RADAR.md`
- `TES/KNOWLEDGE_SOURCE_INDEX.md`
- `TES/EXPERIENCE_STORE.md`
- `TES/06_Research/RADAR_REFRESH_2026-09-14.md`

`TES/DECISION_LOG.md` no cambia porque no se adoptó una tecnología ni cambió una decisión arquitectónica del producto.
