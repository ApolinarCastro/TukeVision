# LOOP-0018P — RESULTADOS DE TESTS FOCALIZADOS, REGRESIÓN, COMPILEALL Y SECRET SCAN

## Entorno

- Interprete: `.venv` portable de TukeVision-portable (LABORATORY), usado por
  convención establecida en loops previos (el `.venv` del BASE está roto).
- CWD: `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision`.
- Comando: `python -m unittest discover -s tests -p "test_*.py"`.

## Tests focalizados LOOP-0018P — `tests/test_activity_layer.py`

Resultado: **39/39 OK** (deterministas, sin cámaras reales, reloj inyectable).

| Área | Tests | Cobertura |
|---|---|---|
| Schema | 11 | creación mínima, campos obligatorios, tipo/estado inválidos, confianza fuera de rango, payload no dict, inmutabilidad, roundtrip, JSON, payload acotado, sin OpenCV |
| Timestamps | 2 | UTC canónico con sufijo Z; reloj inyectable determinista |
| Secretos | 2 | redacción de URL RTSP con credenciales en payload y en metadatos |
| Cola bounded | 7 | drop_oldest, drop_newest, orden FIFO, peek, maxlen/overflow inválidos, layer bounded |
| Aislamiento 4 cámaras | 2 | 4 fuentes lógicas independientes; productor defectuoso aislado |
| Perfiles | 6 | QUALITY/BALANCED/ECONOMY intervalos, calidad>economy análisis, default seguro no continuo, override por cámara, describe auditable |
| Config inválida fail-safe | 5 | perfil inválido, presupuesto inválido, None, garbage, layer con config rota |
| Shutdown y determinismo | 5 | close con stats, operaciones post-close, determinismo, ids únicos/ordenados, consume limit |

## Regresión BASE completa

- Baseline LOOP-0018N: **241 tests** (checkpoint `92e6344`).
- Resultado: **280/280 OK** (241 + 39 nuevos) en 3 ejecuciones consecutivas
  (~24-31s).
- Primera ejecución inicial reportó 1 fallo transitorio; las 3 ejecuciones
  siguientes completas fueron OK. No es regresión de LOOP-0018P (test timing
  preexistente, sin relación con la nueva capa).

## Compileall

`python -m compileall -q src` -> **EXIT=0** (G17 PASS).

## Secret scan

- `grep` sobre `src/observations`: sin matches de `password=` / `rtsp://u:p@` /
  canaries -> SECRET_LEAK=0 (G13 PASS).
- `ActivityObservation.to_dict()` redacta toda cadena del payload con
  `redact_rtsp_url` (defensa en profundidad).

## Hashes SHA-256 de archivos funcionales modificados/creados

```
46E4D89BDDEE212465F0A13BD91E5838660ABD0EF85CF7A05794433CAE49FD3C  src\observations\activity.py
1EE5AEF65EFE01BB8C8BC5FA47D87CB6999FECCAF3960813E1D3D15993B4A5EF  tests\test_activity_layer.py
18310B4E6C1D635F2904095D705C0721B2225968DE99382E9CDAA7ED4F4CE885  config\default.json
```