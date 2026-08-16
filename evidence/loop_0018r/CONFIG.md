# LOOP-0018R — Configuración

Fecha: 2026-08-16

## Bloque `temporal` añadido a `config/default.json`

```json
"temporal": {
  "association_window_ms": 2000,
  "track_timeout_ms": 5000,
  "iou_threshold": 0.05,
  "max_active_tracks": 8,
  "max_completed_history": 32,
  "max_event_refs": 16,
  "max_evidence_refs": 3
}
```

## Semántica

| Parámetro | Default | Significado |
|---|---|---|
| `association_window_ms` | 2000 | Ventana temporal para asociar un evento a un track existente |
| `track_timeout_ms` | 5000 | Sin eventos en este intervalo -> track/activity ENDED |
| `iou_threshold` | 0.05 | IoU mínima para asociación espacial cuando hay bbox |
| `max_active_tracks` | 8 | Tope de tracks activos por cámara (evict oldest) |
| `max_completed_history` | 32 | Tope histórico de tracks completados (FIFO bounded) |
| `max_event_refs` | 16 | Tope de event_refs retenidas por track (últimas N) |
| `max_evidence_refs` | 3 | Tope de evidence refs (first/latest/best) |

## Config-driven (G25) y fail-safe (G27)

- `build_tracker(config)`: sin `temporal` -> defaults conservadores documentados
  (sin bloqueo); bloque con valores inválidos -> `TemporalConfigError` explícito
  (nunca falla silenciosamente con un valor no válido).
- Test: `build_tracker({"association_window_ms": "bogus"})` ->
  `TemporalConfigError` (PASS).
- El diff del config es SOLO este bloque: `git diff HEAD -- config/default.json`
  = +9 líneas. El bloque `inference` de LOOP-0018Q permanece intacto.