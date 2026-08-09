# Preproducción Local (LOOP-0011)

Documenta la preparación de TukeVision para un piloto operativo local
real: trazabilidad de ejecución, validación de configuración, health
check y prueba prolongada controlada. No agrega capacidades de detección
ni modifica la lógica de negocio certificada.

## Qué se añadió

| Elemento | Propósito |
|---|---|
| `src/observability/logging_setup.py` | Logging a archivo (biblioteca estándar `logging`) con RUN_ID por ejecución, rotación y redacción de credenciales |
| `src/app/pipeline.py` | Logging de inicio/fin/errores + validación mínima de configuración + límite opcional de duración |
| `src/ui/controller.py` | Registro de errores y detenciones de la interfaz |
| `scripts/health_check.py` | Diagnóstico local: CONFIG, MODEL, SOURCE, DISK, LOGGING, EVIDENCE_PATH, FINAL_STATUS |
| `scripts/run_long_duration.py` | Prueba prolongada controlada con `MAX_DURATION_SECONDS` (por defecto 1800s) |

## Logging

Cada ejecución crea `logs/tukevision-<RUN_ID>.log` con:

- Inicio: tipo de fuente, en vivo o no, resolución y FPS.
- Fin: conteos (frames, personas, tracks, observaciones, eventos,
  alertas, evidencia) y `final_status`.
- Errores controlados y no controlados (con traceback).
- Detenciones por usuario o por límite de duración.

**Privacidad**: los handlers aplican un formatter que redacta credenciales
embebidas en URLs RTSP (`rtsp://usuario:secreto@host` → `REDACTED`) y
etiquetas `password=`. La prueba `tests/test_observability.py` verifica
que el archivo de log no contiene credenciales.

## Validación de configuración

`Pipeline.__init__` rechaza valores imposibles antes de ejecutar:

- `zone.polygon`: al menos 3 vértices `[x, y]` con números reales.
- `video.max_width` > 0.
- `detection.confidence_threshold` en [0, 1].
- `business.max_stay_seconds` >= 0.
- `alerts.risk_threshold` en [0, 100].

Errores controlados con `PipelineConfigError`.

## Health check

```powershell
python scripts/health_check.py
```

No abre cámaras, no procesa video ni modifica datos. Reporta:

- `CONFIG`: carga y construye el pipeline con la configuración actual.
- `MODEL`: existencia del modelo.
- `SOURCE`: accesibilidad de la webcam (WARN si no disponible).
- `DISK`: tamaño de `data/output`, `data/evidence`, `logs`, `data/temp`.
- `LOGGING`: el directorio de logs es escribible.
- `EVIDENCE_PATH`: accesibilidad de `data/evidence`.
- `FINAL_STATUS`: `OK` si no hay fallos, `ERROR` en caso contrario.

## Prueba prolongada controlada

```powershell
python scripts/run_long_duration.py --seconds 1800 --output data/temp
```

- Procesa la webcam local de forma continua.
- Al alcanzar `MAX_DURATION_SECONDS` termina limpiamente con
  `final_status=DURATION_LIMIT`: se cierran escritor, fuente, detector y
  tracker. No usa `os._exit()` ni terminación forzada.
- Reporta RUN_ID, duración real, frames, detecciones, alertas y evidencia.
- Escribe el video de salida en `data/temp` para no contaminar `data/output`.

Resultado validado en LOOP-0011: `LONG_RUN_DURATION_SECONDS=302`,
`FINAL_STATUS=DURATION_LIMIT`, 0 errores, cierre limpio.

## Evidencia

- La integridad de la evidencia (SHA-256 del fotograma) se mantiene sin
  cambios. Se añadió `tests/test_evidence_store.py::test_failed_frame_write_raises_invalid_evidence`
  para el fallo controlado de escritura.
- La UI sigue abriendo la carpeta de evidencia solo en modo lectura.

## Pruebas

Suite completa: `python -m unittest discover -s tests -p "test_*.py"`.

- `tests/test_observability.py` — RUN_ID, redacción de credenciales,
  creación de archivo de log, idempotencia.
- `tests/test_pipeline.py` — validación de configuración inválida y
  límite de duración (`DURATION_LIMIT`).
- `tests/test_evidence_store.py` — fallo de escritura de evidencia.
