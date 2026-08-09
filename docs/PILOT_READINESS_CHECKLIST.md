# Checklist de Preparación de Piloto (LOOP-0011)

Verificación operativa para ejecutar un piloto local real de TukeVision
con una fuente de observación (webcam local, archivo de video o RTSP).
Cada elemento se comprueba antes de la ejecución del piloto.

## 1. Precondiciones de instalación

- [x] Python virtualenv presente y funcional (`.venv`).
- [x] `pip check` sin dependencias rotas.
- [x] Modelo de detección presente (`models/yolo11n.pt`).
- [x] Configuración válida (`config/default.json`).

## 2. Health check local

Ejecutar `python scripts/health_check.py`:

- [ ] `CONFIG: PASS`
- [ ] `MODEL: PASS`
- [ ] `SOURCE: PASS` (o `WARN` si se usará FILE)
- [ ] `DISK: PASS` (espacio y tamaños de `data/output`, `data/evidence`,
      `logs`, `data/temp`)
- [ ] `LOGGING: PASS`
- [ ] `EVIDENCE_PATH: PASS`
- [ ] `FINAL_STATUS: OK`

## 3. Validaciones de ejecución

- [ ] Suite completa: `python -m unittest discover -s tests -p "test_*.py"`
      → `OK`.
- [ ] SPEC-0001 (archivo local): `run_prototype.py <video>` → `FINAL_STATUS: OK`.
- [ ] LIVE_INPUT (webcam): `run_long_duration.py --seconds <duración>`
      → termina con `FINAL_STATUS: DURATION_LIMIT` y cierre limpio.
- [ ] RTSP: conexión con URL redactada (`RTSP: REDACTED`); sin
      credenciales en pantalla ni en logs.
- [ ] Interfaz local: `run_interface.py` arranca y muestra la pantalla única.

## 4. Operación sostenida

- [ ] Límite de duración configurado (`MAX_DURATION_SECONDS=1800` en el
      piloto). La ejecución nunca queda indefinida.
- [ ] Detención por usuario: `STOPPED_BY_USER` con cierre limpio.
- [ ] Sin errores en el log de la ejecución (`logs/tukevision-<RUN_ID>.log`).
- [ ] Evidencia inmutable bajo `data/evidence/<alert_id>/` con SHA-256.
- [ ] Salida del video de prueba dirigida a `data/temp` (no `data/output`).

## 5. No regresiones garantizadas

- [ ] DETECCIÓN, SEGUIMIENTO, OBSERVACIONES, EVENTOS, RIESGO, ALERTAS y
      EVIDENCIA sin cambios funcionales (la matriz de auditoría de
      LOOP-0011 no detectó GAP en esas capacidades).
- [ ] Equivalencia de salida con y sin `on_frame`:
      `tests/test_pipeline_equivalence.py` → `OK`.
- [ ] Redacción de credenciales verificada por test
      (`tests/test_observability.py`).

## Resultado

Completar cada casilla marcándola `[x]` durante la preparación del
piloto. El piloto solo debe iniciarse si `FINAL_STATUS: OK` en el health
check y la suite de pruebas completa pasa.
