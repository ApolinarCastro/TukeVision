# LOOP-0018N — E02_E05_APPLICABILITY_MATRIX (PASO 2)

Clasificación final de cada E-xx según las 8 categorías permitidas.

| E-xx | Capacidad | Clasificación | Justificación | Acción dentro de este LOOP | Estado TES |
|---|---|---|---|---|---|
| E-02 | Trajectory + flow IN/OUT/INSIDE | **REUSABLE_WITH_ADAPTATION** | Código limpio, 0 libs nuevas, modelo de datos correcto (camera_id en TrackTrajectory). La integración en `pipeline.py`/`controller.py` requiere adaptación a multicámara (cada cámara con su TrajectoryStore). Sin tests → hay que escribirlos. | NO migrar ahora. Diseñado como capa de datos multicámara en el Product Core. | EXPERIMENTAL → REUTILIZABLE (diseñado) |
| E-03 | Identity/ReID por apariencia | **REQUIRES_EXTERNAL_EXTENSION / REQUIRES_DECISION** | Entra en conflicto directo con DEC-0013 (identidades persistentes vs "no identifica personas"; aunque no es facial, crea identity_id persistente). Además `_PROJECT_ROOT` hardcodea ruta portable. Requiere DEC-0013 revisado + encoders portables. | NO implementar. Registrar bloqueo de gobernanza. | EXPERIMENTAL → REQUIERE_DECISION |
| E-04 | Command Center UI (grid 4x4, fullscreen, canal) | **REUSABLE_WITH_ADAPTATION** | UI Tkinter madura, 0 libs nuevas. Depende de que exista la capa multicámara (SourceManager + estado por cámara). El bloque flow/people/active_tracks del controller depende de E-02. | NO migrar ahora. Diseñado como presentación del Command Center tras multicámara. | EXPERIMENTAL → REUTILIZABLE (diseñado) |
| E-05 | Quality engine (subtype main/sub por perfil) | **REUSABLE_WITH_ADAPTATION** | Lógica de decisión válida. Los datos hardcodeados (`_register_audit_capabilities`) deben reemplazarse por capacidades medidas dinámicamente (resource_budget). | NO migrar ahora. Diseñado como fuente de política de stream en multicámara. | EXPERIMENTAL → REUTILIZABLE (diseñado) |

## Resultado

- ALREADY_EXISTS_IN_BASE: 0
- REUSABLE_AS_IS: 0
- REUSABLE_WITH_ADAPTATION: 3 (E-02, E-04, E-05)
- REQUIRES_EXTERNAL_EXTENSION: 1 (E-03, condicionado a decisión de gobernanza)
- CUSTOM_DEVELOPMENT_REQUIRED: 0
- OBSOLETE: 0
- REJECTED: 0

**E02_E05_100_PERCENT_CLASSIFIED = PASS (G3)**

## Regla de activación
Ningún E-xx se migra en este LOOP. La clasificación define su futuro dentro de
`FIRST_PRODUCT_DELIVERY` y el Product Core. Solo E-02/E-05 son candidatos de
integración temprana post-multicámara; E-04 tras SourceManager; E-03 solo con
decisión humana sobre DEC-0013.