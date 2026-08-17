# LOOP-0019A-R2 — evidencia TDD

## Journey

Como operador, quiero que la aplicación multicámara presente y conserve los
resultados reales y sparse del pipeline, para verificar detección, tracking,
temporal, comportamiento, riesgo y evidencia sin datos fabricados.

## RED → GREEN

| Garantía | RED | GREEN |
|---|---|---|
| El conteo se lee del contrato `InferenceEvent.metadata` | adaptador inexistente | PASS |
| Un frame sin evento no borra la última analítica real | `0 != 2` | PASS |
| Traza bounded alcanza modelo y renderer | módulo inexistente | PASS |
| STOP sigue el estado autostart multicámara | helper inexistente | PASS |
| Controles legacy no se presentan | helper inexistente | PASS |
| Todos los paneles tienen tamaño estable sin ampliar fuente | helper inexistente | PASS |

Comandos ejecutados:

- `python -m unittest tests.test_multicamera_view tests.test_multicamera_entrypoint -v`
- `python -m unittest discover -s tests`
- `python -m compileall -q src scripts tests`

Resultado final: 428 tests PASS; 4 skips preexistentes del backend real opcional.
No se ejecutó medición de coverage porque el proyecto no incluye runner de
coverage en el entorno; la regresión completa sí fue ejecutada.
