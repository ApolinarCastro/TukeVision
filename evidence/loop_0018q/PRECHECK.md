# LOOP-0018Q — Precheck (evidencia)

Fecha: 2026-08-16
Branch: `product/loop-0018q-selective-inference-events`
Checkpoint base: `c7432313536d931bea703692714a09138654b3e7`

## Verificaciones previas

| Verificación | Resultado |
|---|---|
| Branch creada desde checkpoint certificado | PASS |
| E-01 `src/capture/live_sources.py` git-hash `6a9ae7e1187c2b8644b3f9f73abbcb5d689b61a7` | INTACTO (re-verificado al cierre) |
| SourceManager `src/capture/source_manager.py` git-hash `29e0274beac2f623fcd24feca7f9c9bf1c85f33e` | INTACTO (re-verificado al cierre) |
| `config/default.json` base `d7b2f8835a04d44df90a94b6b91fe75759a4126d` | INTACTO antes de editar (diff final = solo bloque `inference`) |
| Regresión base previa | 280/280 OK |
| Entorno de tests | portable `.venv` Python 3.12.10, ultralytics 8.4.115, cv2 5.0.0 (BASE `.venv` roto: pyvenv apunta a `C:\Users\Tuke\...`) |
| Modelo real `models/yolo11n.pt` (5.6 MB) | PRESENTE |
| Imagen real de prueba `data/temp/zidane.jpg` (personas) | PRESENTE (untracked, sin tocar) |
| Backend YOLO real verificado en precheck | 2 detecciones person (1372 ms incl. carga de modelo) |

## Untracked protegidos (NO se tocan)

- `evidence/loop_0018m_r1/`
- `src/capture/live_sources.BASE_preE01.bak.py`

## Notas de integridad

- El hash de precheck registrado para E-01/SourceManager corresponde al hash de
  blob git (`git hash-object`), no al SHA-1 crudo de archivo. La verificación de
  cierre con `git hash-object` devuelve los mismos valores -> contenido inmutable.
- `git diff HEAD` de los archivos de captura: vacío (sin cambios).
- `config/default.json`: diff = +14 líneas, SOLO el bloque `inference`.