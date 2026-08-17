# BASE RUNTIME RECONSTRUCTION (C2) — LOOP-0018T

**LOOP:** 0018T · **Fase:** 2 (C2) · **Fecha:** 2026-08-16
**BASE_CODE:** `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision`

---

## 1. Problema (precheck, LOOP-0018S H4)

El `.venv` del BASE estaba roto:

```
home = C:\Users\Tuke\AppData\Local\Programs\Python\Python312   (NO existe en este PC)
executable = C:\Users\Tuke\AppData\Local\Programs\Python\Python312\python.exe
command = C:\Users\Tuke\AppData\Local\Programs\Python\Python312\python.exe -m venv D:\TukeVision\.venv
version = 3.12.9
```

El redirector `python.exe` fallaba: `No Python at 'C:\Users\Tuke\...'`. Los loops
anteriores usaron el `.venv` PORTABLE como runner (laboratorio), NO el BASE.

## 2. Decisión C2 (per LOOP-0018S condición C2)

Regenerar el venv BASE **desde cero con el intérprete del sistema**, siguiendo el
proceso oficial por manifests (`requirements.txt` / `requirements.lock.txt`),
sin copiar físicamente el `.venv` portable.

- Intérprete base: `C:\Users\ASUS Zenbook\AppData\Local\Programs\Python\Python312\python.exe`
  (Python **3.12.10** — misma versión que el portable certificado).
- Comando: `python -m venv .venv` y `pip install -r requirements.txt`.
- Después: verificación por imports, regresión completa y compileall con el
  intérprete BASE (no portable).

## 3. Reconstrucción

| Paso | Comando | Resultado |
|---|---|---|
| 1 | `Remove-Item .venv -Recurse -Force` | limpieza del venv roto |
| 2 | `python -m venv .venv` | venv creado (3.12.10) |
| 3 | `.venv\Scripts\python -m pip install -r requirements.txt` | instalado OK |

Manifests usados:
- `requirements.txt`: ultralytics==8.4.115, supervision==0.29.1, trackers==2.5.0.post0, opencv-python==5.0.0.93
- `requirements.lock.txt`: lock completo presente (fuente de referencia de versiones).

## 4. Versiones críticas certificadas (BASE vs evidencia portable)

| Paquete | BASE `.venv` (nuevo) | Portable `.venv` (evidencia) | Coincide |
|---|---|---|---|
| python | 3.12.10 | 3.12.10 | SÍ |
| cv2 | 5.0.0 | 5.0.0 | SÍ |
| numpy | 2.5.2 | 2.5.2 | SÍ |
| torch | 2.13.0+cpu | 2.13.0+cpu | SÍ |
| ultralytics | 8.4.115 | 8.4.115 | SÍ |
| supervision | 0.29.1 | 0.29.1 | SÍ |
| trackers | 2.5.0.post0 | 2.5.0.post0 | SÍ |

Lista completa de paquetes instalados en `base_runtime_packages.txt` (46 líneas, `pip freeze`).

## 5. Verificación con el runtime BASE (NO portable)

| Verificación | Comando | Resultado |
|---|---|---|
| Imports críticos | `.venv\Scripts\python -c "import ..."` | ALL_IMPORTS_OK |
| Regresión completa | `.venv\Scripts\python -m unittest discover -s tests` | **370/370 PASS** (25.1s) |
| COMPILEALL | `.venv\Scripts\python -m compileall -q src scripts tests` | COMPILEALL_OK_BASE |

NOTA: la regresión de 370 tests (359 baseline + 11 de C1) pasa con el intérprete
BASE; ya no se usa el portable como runner estándar del BASE.

## 6. Trazabilidad de independencia

- `PORTABLE_PYTHON_USED_FOR_TESTS` (desde C2): **NO** (los tests usan `.venv` BASE).
- `PORTABLE_PYTHON_USED_FOR_BUILD`: **NO** (el build usará `.venv` BASE; ver Fase 5).
- No se copió ni se referenció ningún artefacto del `.venv` portable.
- El `.venv` portable queda como LABORATORIO/REFERENCIA únicamente.

## 7. Conclusión C2

> **C2 = CLOSED**: venv BASE regenerado desde cero con Python 3.12.10 del sistema,
> versiones críticas idénticas al runtime portable certificado, 370/370 PASS con
> el intérprete BASE, compileall OK, imports OK. Proceso oficial por manifests,
> sin copia del venv portable.

— Fin de base_runtime_reconstruction.md (LOOP-0018T)