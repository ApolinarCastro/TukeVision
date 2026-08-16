# LOOP-0018P — CONFIGURACIÓN DE POLÍTICAS (OBSERVATION)

## Bloques `config/default.json` añadidos (extensión del BASE)

```json
"observation": {
  "default_profile": "BALANCED",
  "profiles": {
    "QUALITY":  { "max_analysis_fps": 5.0 },
    "BALANCED": { "max_analysis_fps": 2.0 },
    "ECONOMY":  { "max_analysis_fps": 1.0 }
  }
}
```

## Semántica

- `default_profile`: perfil aplicado a cámaras sin override. Valor seguro:
  BALANCED (NO habilita inferencia continua 15fps x 4; restricción LOOP-0018N).
- `profiles.<PERFIL>.max_analysis_fps`: presupuesto máximo de análisis por cámara.
- Intervalo de sampling por cámara (determinista):
  `interval = max(1, round(fps_real / max_analysis_fps))`
  - QUALITY a 15 fps -> interval 3 (~5 análisis/s)
  - BALANCED a 15 fps -> interval 8 (~2 análisis/s)
  - ECONOMY a 15 fps -> interval 15 (~1 análisis/s)
  - Si fps_real no se conoce (<= 0) -> fallback fps=15 (seguro).

## Fail-safe (config inválida o ausente)

| Condición | Resultado |
|---|---|
| `default_profile` no válido | -> BALANCED |
| `max_analysis_fps` no numérico / fuera de rango | -> valor seguro del perfil (clamp sanitizador) |
| `profiles` no es dict / garbage | -> perfiles seguros por defecto |
| `cameras` override no válido | -> ignorado (perfil default) |
| Config ausente (None) | -> defaults seguros |

## Pruebas de configuración (tests/test_activity_layer.py)

- `test_invalid_default_profile_falls_back`
- `test_invalid_max_analysis_fps_clamped`
- `test_none_config_is_safe`
- `test_garbage_config_is_safe`
- `test_layer_with_broken_config_is_safe`
- `test_default_profile_is_safe_not_continuous` (<= 8 análisis en 4s a 15fps)
- `test_per_camera_profile_override`
- `test_policy_describe_auditable`

## Consumo

- `ActivityLayer(config=...)` extrae `config["observation"]` y lo pasa a
  `ObservationPolicy`. Sin configuración, se usan los defaults seguros.
- `ObservationPolicy` no modifica SourceManager; solo usa `fps` real como
  entrada de decisión.