# LOOP-0018P — ARQUITECTURA MÍNIMA DE LA ACTIVITY / OBSERVATION LAYER

## Principio rector

    CAPTURE -> OBSERVATION -> POLICY -> INFERENCE -> EVENT -> EVIDENCE

En LOOP-0018P se implementan y dejan operativos OBSERVATION y POLICY mínima.
INFERENCE (detección selectiva), EVENT y EVIDENCE quedan preparados vía
contratos mínimos (`producer` callable, `evidence_ref` opcional) sin adelantar
su implementación.

## Componentes (un solo módulo: `src/observations/activity.py`)

### 1. `ActivityObservation` (schema canónico, frozen/immutable)

| Campo | Tipo | Contrato |
|---|---|---|
| `observation_id` | str | Identificador único determinista (`OBS-{camera_id}-{seq:06d}`) |
| `camera_id` | str | Identidad lógica de fuente/cámara (inequívoca, aislada por cámara) |
| `timestamp` | str | UTC ISO-8601 con sufijo Z (reloj inyectable para determinismo) |
| `observation_type` | str | Categoría: FRAME_SAMPLE / SIGNAL / STATE_CHANGE |
| `state` | str | ACTIVE / STALE / DEGRADED / ERROR |
| `payload` | dict | Acotado (JSON, <= 4096 bytes serializado), sin frames ni OpenCV |
| `confidence` | float? | Nivel de confianza cuando corresponde (0..1) |
| `origin` | str | Origen/productor (`activity:sampler`) |
| `evidence_ref` | str? | Referencia opcional a evidencia (contrato; EVIDENCE posterior) |

Garantías: no contiene credenciales (redact en serialización), no contiene
objetos OpenCV (JSON-serializable validado), inmutable, serializable
(`to_dict`/`from_dict` roundtrip).

### 2. `BoundedObservationQueue` (cola acotada por cámara)

- FIFO por cámara con `maxlen` (memoria limitada, sin crecimiento ilimitado).
- Política de overflow EXPLÍCITA: `drop_oldest` (default) o `drop_newest`.
- Contador determinista de descartados (`dropped`).
- Aislamiento: una cámara lenta/defectuosa no afecta las colas de las demás.

### 3. `ObservationPolicy` (política CONFIG-DRIVEN)

- Perfiles: QUALITY (5 fps análisis) / BALANCED (2 fps) / ECONOMY (1 fps).
- Configurable vía `config/default.json` bloque `observation` (perfil por defecto
  seguro = BALANCED) y override por cámara.
- Decisión determinista: `interval = max(1, round(fps_real / max_analysis_fps))`,
  `should_analyze = (frame_index % interval) == 0`.
- NO modifica SourceManager: consulta fps real (composición vía health()).
- Fail-safe: config inválida/ausente -> default BALANCED + clamp sanitizador de
  presupuestos. Cumple restricción LOOP-0018N (sin inferencia continua 15fps x 4).
- `describe()` expone la decisión de forma auditable.

### 4. `ActivityLayer` (orquestación)

- `register_camera(camera_id, fps)` / `register_from_source_manager(sm)`:
  composición con SourceManager (inventario público sin credenciales + fps real).
- `feed(camera_id, frame_index, metadata, frame)`:
  aplica política de sampling; si selecciona, invoca al productor y encola.
  El `frame` se pasa solo al productor (inferencia selectiva futura), NUNCA se
  almacena ni serializa.
- `consume` / `peek` / `queued` / `stats` / `camera_state`: consulta y consumo.
- Aislamiento: productor defectuoso de UNA cámara -> estado ERROR de esa cámara;
  las demás siguen intactas (producer errors contabilizados).
- `close()`: shutdown limpio (stats finales + colas vaciadas).

## Contrato del productor (INFERENCE selectiva futura)

```python
producer(camera_id: str, frame_index: int, metadata: dict | None) -> dict | None
```

- Devuelve payload acotado de la observación o None (no observar).
- El productor por defecto (`_default_producer`) es DETERMINISTA y NO ejecuta
  YOLO: solo registra frame_index + metadatos acotados. La certificación del
  loop usa productores sintéticos, conforme a la directiva.

## Conectividad con SourceManager (composición, no reescritura)

- `ActivityLayer.register_from_source_manager(sm)` llama a
  `sm.list_sources()` (inventario redactado) y `sm.health(camera_id).fps`
  (fps real) para configurar el sampling. El lifecycle interno de RTSPSource,
  OpenCV, FFmpeg y el anti-double-free NO se tocan.

## Decisiones de diseño (menor cambio posible)

- Un solo módulo funcional nuevo + un test file + bloque de config.
- Sin herencia de SourceManager; composición.
- Sin framework interno; dataclasses + deque + threading.RLock de stdlib.
- Sin dependencias nuevas (NEW_DEPENDENCIES=0).
- Timestamps UTC canónicos con reloj inyectable -> determinismo en tests.
- Serialización con redacción de credenciales en TODA cadena del payload.