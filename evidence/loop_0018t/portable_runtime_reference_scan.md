# PORTABLE RUNTIME REFERENCE SCAN — LOOP-0018T

**Fecha:** 2026-08-16 · **Base:** `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision`

## Búsqueda

Patrón `TukeVision-portable` sobre archivos `.py/.json/.ps1/.md/.txt` de:
`src/`, `config/`, `scripts/`, `install/` (runtime BASE, sin tests/dist).

## Resultado

| Ámbito | Coincidencias |
|---|---|
| `src/` | 0 |
| `config/` | 0 |
| `scripts/` | 0 |
| `install/` | 1 (benigna) |

Única coincidencia: `install/package.ps1`
- Línea 4: comentario `# dist/TukeVision-portable.zip.`
- Línea 123: `$zipPath = Join-Path $distDir "TukeVision-portable.zip"`

## Clasificación

`TukeVision-portable.zip` es el **nombre del artefacto oficial de distribución**
(heredado del flujo portable, definido en `package.ps1`), NO una referencia al
runtime portable. No es código de runtime ejecutable ni un path.

## Veredicto

> **PORTABLE_RUNTIME_REFERENCES = 0** en el runtime BASE (src/config/scripts).
> BASE_RUNTIME_INDEPENDENT_FROM_PORTABLE = **YES**.

— Fin de portable_runtime_reference_scan.md (LOOP-0018T)