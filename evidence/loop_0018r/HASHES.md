# LOOP-0018R — Hashes finales

Fecha: 2026-08-16

## Archivos nuevos LOOP-0018R

| Archivo | git-hash |
|---|---|
| `src/temporal/__init__.py` | `bb1e743849a835158a99ccf9dc2f7b47189bfe8c` |
| `src/temporal/contract.py` | `f65ba7046cf60191266e39dcbd54d5d5478aba76` |
| `src/temporal/tracker.py` | `ca51c4b9a7974f1b27e358691b8e572c14185c1d` |
| `tests/test_temporal_tracking.py` | `20d080e1a7b8607e526c0df4f4da8fa7c6d92bac` |
| `config/default.json` | `f23e30429df7201c515bfe850c8d1328a44be2d8` |

## Componentes certificados (deben permanecer INTACTOS)

| Archivo | git-hash esperado | Estado |
|---|---|---|
| `src/capture/live_sources.py` (E-01) | `6a9ae7e1187c2b8644b3f9f73abbcb5d689b61a7` | INTACTO |
| `src/capture/source_manager.py` | `29e0274beac2f623fcd24feca7f9c9bf1c85f33e` | INTACTO |
| `src/observations/activity.py` | `114b6a3715024d7f142f6b7082950f6fffc4e41b` | INTACTO |
| `src/inference/selective.py` | `855f20bd421289b442d66941365d7dec5ba09241` | INTACTO |
| `src/inference/contract.py` | `3fa0d4ef62beeca6d9b3f8dfa941576e213b6e7b` | INTACTO |
| `src/inference/events.py` | `8a2594d2838a647cf5d8dec7f8e40614f364a4dc` | INTACTO |
| `src/inference/engines.py` | `5457a777c035965ed016a9aca919154a7ecf41d5` | INTACTO |
| `src/inference/__init__.py` | `193ee3cc6bdfcfcde27e39bc6bc958b2aaad12eb` | INTACTO |

## Diff scope

`git diff HEAD` (worktree, tras `git add -N`):
- `config/default.json`: +9 líneas, SOLO bloque `temporal`.
- `src/temporal/`: 3 archivos nuevos.
- `tests/test_temporal_tracking.py`: nuevo.
- Certificado diffs (capture/observations/inference): vacío.
- Untracked protegidos (`evidence/loop_0018m_r1/`,
  `src/capture/live_sources.BASE_preE01.bak.py`): presentes, NO tocados.

## SECRET SCAN (G29)

Patrones rtsp://user:pass@, password=, api_key, secret, PRIVATE KEY:
sin hits reales en `src/`, `config/`, `tests/` nuevos. Los únicos matches son
canarios de tests (usuarios/contraseñas falsos) y el propio código de redacción
(`rtsp_url.py`, `logging_setup.py`) — esperado. **PASS (0 leaks).**

## NEW_DEPENDENCIES (G27)

`src/temporal/*` usa SOLO stdlib (`datetime`, `json`, `typing`, `dataclasses`,
`collections`). pyproject/requirements sin cambios. **NEW_DEPENDENCIES=0.**