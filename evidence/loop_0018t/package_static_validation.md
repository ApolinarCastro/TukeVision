# PACKAGE STATIC VALIDATION (C3) — LOOP-0018T

**Fecha:** 2026-08-16 · **Paquete:** `dist\TukeVision` (rebuild desde HEAD `cfad931`)
**Método:** análisis estático de archivos `.py/.json/.ps1/.md/.txt` del paquete.

## 1. Referencias a portable/rutas de usuario

Búsqueda de patrones: `TukeVision-portable`, `Users\ASUS`, `ASUS Zenbook`, `D:\TukeVision`.

| Resultado | Detalle |
|---|---|
| Referencias PORTABLE_RUNTIME | 0 en runtime (`src/`, `config/`, `scripts/`, `docs/`) |
| Coincidencias encontradas | 2, ambas benignas y NO de runtime |
| — `install/package.ps1` | `dist/TukeVision-portable.zip` = nombre OFICIAL del artefacto de distribución (no el runtime portable) |
| — `install/verify_package.ps1` | comentario de ejemplo de uso (`-PackageDir "D:\TukeVision\..."`) |

**Conclusión:** PORTABLE_RUNTIME_REFERENCES = 0 en el runtime del paquete.

## 2. Secretos / credenciales

Búsqueda de patrones: `ASUS`, `admin:`, `password =`, `rtsp://user:pass@`, URLs con credenciales.

- **12 coincidencias**, todas clasificadas como seguras (idénticas al BASE que pasó SECRET_LEAK=0):
  - Ejemplos de documentación con credenciales ficticias (`rtsp://user:pass@`, `usuario:clave@`, `REDACTED:REDACTED`).
  - Canarios de test (`SECRET_CANARY_*`, IP de documentación `192.0.2.10`).
  - Código legítimo de manejo de credenciales (`rtsp_url.py`, `source_manager.py` campo password, `logging_setup.py` redacción).
- **0 credenciales reales, 0 DVR/hardcodeadas, 0 rutas de usuario.**
- Test oficial `tests/test_secret_leak.py` y `test_no_secrets_in_repo` → PASS (dentro de la regresión 370/370).

## 3. Estructura / exclusiones

`install/verify_package.ps1` → **VERIFY_STATUS: OK**:
- MODEL_HASH_VALID: YES (yolo11n.pt = 0EBBC80D...)
- requirements.txt / requirements.lock.txt presentes: YES
- pipeline/tk_view/controller/run_interface/config/start/install scripts: YES
- Exclusiones (.git, .venv, tests, videos, data temp): OK

`tests/test_portable_package.py` → PASS (14/14): estructura requerida presente, exclusiones ausentes, sin `__pycache__`, zip existe, manifest válido.

## 4. MANIFEST oficial (nuevo)

```json
{
  "package_version": "0.1.0",
  "build_date": "2026-08-16",
  "git_head": "cfad93163b9fe1b992e87026b0adbb437c518cee",
  "spec_certified_base": "cf876a9",
  "python_required": "3.12.x",
  "model_filename": "models/yolo11n.pt",
  "model_sha256": "0EBBC80D4A7680D14987A577CD21342B65ECFD94632BD9A8DA63AE6417644EE1",
  "requirements_sha256": "8E5D54E761F1293AEB3A46F48842B72FC69DCED9057529346DC7F7735CDD433F"
}
```

git_head correcto (cfad931, HEAD actual) — **se corrige el OUTDATED (H2/LOOP-0018S)**.

## 5. Componentes PRODUCT ADVANCE en el paquete

| Componente | Presente | Hash coincide con BASE |
|---|---|---|
| src/capture/source_manager.py | SÍ | SÍ |
| src/observations/activity.py | SÍ | SÍ |
| src/inference/selective.py | SÍ | SÍ |
| src/inference/engines.py | SÍ | SÍ |
| src/temporal/tracker.py | SÍ | SÍ |
| src/app/advance_chain.py (C1) | SÍ | SÍ |
| src/capture/live_sources.py (E-01) | SÍ | SÍ (git blob 6a9ae7e...) |

## 6. Conclusión

> Validación estática del paquete: **PASS**. Sin referencias portable en runtime,
> sin credenciales reales, manifest con git_head HEAD actual, componentes advance
> incluidos, E-01 idéntico al fuente, verify_package OK.

— Fin de package_static_validation.md (LOOP-0018T)