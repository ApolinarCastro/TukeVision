# LOOP-0018N — E02_E05_MANIFEST (PASO 2)

Identificación exacta de E-02..E-05 a partir de `certified_change_map.md`,
`experimental_e01_e05_map.md` y el código real de PORTABLE. Sin etiquetas abstractas.

---

## E-02 — Retail Trajectory (trajectory + flow)

**Fuente portable:** `src/retail/trajectory.py` (6069 b, 175 líneas).

**Símbolos:**
- `TrajectoryPoint` (frozen dataclass): track_id, timestamp, centroid_x/y, zone_id, dwell_seconds.
- `TrackTrajectory`: points[], first_seen, last_seen, total_dwell_seconds, zone_visits.
  - `add_point`, `get_current_position`, `get_zone_history`.
- `FlowCounter`: entries/exits/current_inside por zona.
  - `record_entry`, `record_exit`, `get_entries`, `get_exits`, `get_current_inside_count`, `reset`.
- `TrajectoryStore`: retención limitada (max_points_per_track=300, max_tracks=100).
  - `update`, `record_zone_entry/exit`, `get_trajectory`, `get_all_trajectories`,
    `get_active_tracks`, `clear`, `get_flow_summary`.

**Integración portable:** `src/app/pipeline.py` líneas 185-193 (instancia + property),
396-408 (record_entry/exit + update por objeto), 477 (flow_summary), 495-497 (FrameSnapshot).

**Dependencias:** solo stdlib (dataclasses, datetime, typing, collections). SIN nuevas libs.

**Tests:** NINGUNO en portable (búsqueda de TrajectoryStore/FlowCounter en scripts/test_*.py = 0).

**Capacidad funcional:** historial de posiciones por track, contadores IN/OUT/INSIDE por zona,
consulta de trayectoria. NO genera alertas/eventos (capa de datos objetiva).

**Estado real:** EXPERIMENTAL, sin reporte PASS (LOOP-0017E). No está en BASE.

---

## E-03 — Identity / ReID (Fase 1)

**Fuente portable:** `src/identity/` (4 archivos):
- `encoder.py` (2807 b): `HistogramEncoder` (HSV 16x8x8 → 1024-d L2), `YoloBackboneEncoder`
  (backbone YOLO11n → 256-d L2, carga lazy ultralytics). **NOTA:** `_PROJECT_ROOT` hardcodea
  `C:\Users\ASUS Zenbook\Documents\TukeVision-portable` (línea 17) → NO portable a BASE tal cual.
- `matcher.py` (1763 b): `cosine_similarity`, `Matcher` con MATCH/GREY/NEW (umbrales 0.90/0.85).
- `identity_manager.py` (13041 b): `IdentityConfig`, `TrackIdentity`, `IdentityManager`
  (galería en memoria thread-safe con RLock; lost-buffer re-entrada; dedupe de visitas
  reentry_min_seconds=30; TTL 24h; snapshots para UI).
- `__init__.py` (766 b): exporta la API.

**Integración portable:** `src/app/pipeline.py` líneas 33-34 (imports IdentityManager/Matcher),
95-96 (FrameSnapshot unique_identities/revisits).

**Dependencias:** cv2, numpy (presentes en BASE), ultralytics (solo YoloBackboneEncoder, lazy).
Nuevas libs: NINGUNA.

**Tests:** NINGUNO en portable.

**Capacidad funcional:** re-identificación por apariencia (no facial) para deduplicar conteos
en re-entradas y futuro across-cameras.

**Conflicto de gobierno:** DEC-0013 ("El sistema no identifica personas") prohíbe identificación
mediante **reconocimiento facial**; E-03 usa embeddings de apariencia (no facial), pero crea
identidades persistentes (identity_id) → requiere conciliación con DEC-0013/0018/0019 antes de
cualquier adopción de producto.

**Estado real:** EXPERIMENTAL, sin reporte PASS (LOOP-0019). No está en BASE.

---

## E-04 — Command Center UI

**Fuente portable:**
- `src/ui/tk_view.py` (43272 b, 1031 líneas) vs BASE (12383 b): 29 símbolos PORT_ONLY:
  `camera_label`, `camera_status_color`, `grid_safe_limit`, `quality_label`,
  `_build_cameras_panel`, `_build_grid_tiles`, `_build_intel_panel`, `_set_view_mode`,
  `_on_tile_resize`, `_draw_tile`, `_refresh_tiles`, `_toggle_fullscreen`, `_close_fullscreen`,
  `_on_select_channel`, `_on_channel_var_change`, `_on_focus_channel`, `_update_camera_rows`,
  `_render_intel`, etc.
- `src/ui/state.py` (3034 b): campos adicionales `people`, `active_tracks`.
- `src/ui/controller.py`: bloque `people`/`active_tracks` (líneas 198-199, 254-255) y bloque
  flow metrics (262-275, dependiente de E-02).

**Dependencias:** tkinter (stdlib), cv2 (presente). SIN nuevas libs.

**Tests:** `scripts/test_command_center_ui.py`, `scripts/test_ui_visual.py` existen en portable
pero dependen de la UI subyacente (plan LOOP-0018J FASE 3 las condicionó a migrar E-04).

**Capacidad funcional:** selector de canal 1-16, grid 4x4, fullscreen, panel intel,
label de cámara/estado, enfoque por canal.

**Estado real:** EXPERIMENTAL, sin reporte PASS (LOOP-0017B, solo PNGs de evidencia). No está en BASE.

---

## E-05 — Video Quality Engine

**Fuente portable:** `src/capture/quality_engine.py` (7121 b, 204 líneas).

**Símbolos:**
- `QualityProfile` (ECONOMY/QUALITY/AUTO), `StreamType` (MAIN=0/SUB=1).
- `CameraStreamCapability` (frozen): camera_id, main/sub resolution/fps/stable, last_tested.
- `VideoQualityEngine`: `register_capability`, `get_stream_type`, `get_subtype`,
  `get_fallback_subtype`, `set_profile`, `set_focus_camera`.
- `get_quality_engine()` singleton con `_register_audit_capabilities` (datos hardcodeados de
  auditoría LOOP-0017: CAM1/5/7 estables, resto sin datos).

**Dependencias:** stdlib (dataclasses, enum, typing). SIN nuevas libs.

**Tests:** NINGUNO en portable.

**Capacidad funcional:** decidir subtype (main/sub) según perfil y contexto multiview/focus,
con fallback controlado. NO inventa resolución, NO upscaling.

**Estado real:** EXPERIMENTAL, sin reporte PASS. No está en BASE.

---

## Resumen de clasificación (resultado PASO 2)

| E-xx | Archivos | Tests | Nuevas libs | Clasificación inicial |
|---|---|---|---|---|
| E-02 | `src/retail/trajectory.py` + pipeline | 0 | 0 | REUSABLE_WITH_ADAPTATION (integración pipeline/controller) |
| E-03 | `src/identity/**` (4) + pipeline | 0 | 0 (ultralytics ya activo) | REQUIRES_DECISION (DEC-0013) → ver matriz |
| E-04 | `tk_view.py` + `state.py` + `controller.py` | 2 (condicionados) | 0 | REUSABLE_WITH_ADAPTATION (depende de multicámara) |
| E-05 | `src/capture/quality_engine.py` | 0 | 0 | REUSABLE_WITH_ADAPTATION (datos físicos → dinámicos) |