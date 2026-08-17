# OFFICIAL EXECUTABLE NAMING — LOOP-0018U

**Fecha:** 2026-08-16

## Estado del build oficial certificado

| Item | Valor |
|---|---|
| Build disponible | **YES** (`dist\TukeVision\` 91 archivos + `dist\TukeVision-portable.zip` 4.93 MB) |
| Zip SHA256 | `E4DC8CA8BC355D2BDFC23EF77BC1398551DA5EA1167C9A17313D7CAF997FB2C3` |
| MANIFEST git_head | `cfad93163b9fe1b992e87026b0adbb437c518cee` |
| Ejecutable operativo post-delete | **YES** (smoke: arranque + 2 frames + apagado limpio STOPPED_BY_USER) |
| Dependencia de paths portable | **NO** (DEPENDS_ON_PORTABLE_PATH_HITS=0 en dist) |

## Nota de naming

- El nombre histórico `TukeVision-portable.zip` se mantiene como **artefacto
  certificado** de distribución (mecanismo de packaging BASE en `install\package.ps1`).
- NO se abre otro sistema de packaging en este loop.
- Cuando el proyecto disponga de una convención oficial de release, se
  documentará la necesidad de renombrar/rebuild el artefacto; queda pendiente
  de decisión humana (fuera de este loop).
- `OFFICIAL_EXECUTABLE_DEPENDS_ON_PORTABLE_PATH = NO`
- `OFFICIAL_EXECUTABLE = PASS`

— Fin de oficial_executable note (LOOP-0018U)