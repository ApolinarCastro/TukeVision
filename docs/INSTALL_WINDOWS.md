# Instalación de TukeVision en Windows

Guía en lenguaje sencillo para instalar y ejecutar TukeVision en una PC
Windows 10/11 de 64 bits.

> **Importante**: TukeVision es un paquete técnico portable, no un producto
> empresarial instalado. La versión de paquete es `0.1.0`.

## Requisitos

- Windows 10/11 de 64 bits.
- Python 3.12.x (64 bits). No se descarga automáticamente.
- ~4 GB de RAM como mínimo experimental.
- ~5 GB de espacio libre en disco.
- Git (opcional).

## 1. Preflight (verificación previa)

Verifica que la PC cumple los requisitos. Solo inspecciona; no modifica nada.

```powershell
powershell.exe -ExecutionPolicy Bypass -File install\preflight.ps1
```

Busque `FINAL_STATUS: READY` (o `WARNING` con advertencias no bloqueantes).
Si aparece `BLOCKED`, corrija el problema indicado antes de continuar.

## 2. Instalación

Crea el entorno virtual, instala las dependencias y verifica el modelo.

```powershell
powershell.exe -ExecutionPolicy Bypass -File install\install.ps1
```

El instalador:

1. Ejecuta el preflight.
2. Crea `.venv` con Python 3.12.
3. Instala `requirements.txt` (solo dependencias directas versionadas).
4. Ejecuta `pip check`.
5. Verifica imports críticos (`cv2`, `ultralytics`, `supervision`,
   `trackers`, `tkinter`).
6. Verifica el modelo y su hash SHA-256.
7. Ejecuta el diagnóstico.

Si algo falla, el mensaje indica el motivo (`PYTHON_312_REQUIRED`,
`MODEL_MISSING`, `MODEL_HASH_MISMATCH`, `BLOCKED_BY_DEPENDENCY`).

## 3. Diagnóstico

Comprueba entorno, imports, modelo, configuración, directorios y webcam.

```powershell
powershell.exe -ExecutionPolicy Bypass -File install\diagnose.ps1
```

La webcam es opcional: si no existe, muestra
`WEBCAM_STATUS: NOT_AVAILABLE` y no bloquea la instalación.

## 4. Inicio

Un solo comando inicia la interfaz sin necesidad de activar el entorno
manual:

```powershell
powershell.exe -ExecutionPolicy Bypass -File start_tukevision.ps1
```

También puede crear un acceso directo hacia:

```
powershell.exe -ExecutionPolicy Bypass -File "C:\ruta\a\TukeVision\start_tukevision.ps1"
```

## 5. Seleccionar fuente

Dentro de la aplicación elija la fuente:

- **Archivo (FILE)**: seleccione un video local de `data/input/`.
- **Webcam (WEBCAM)**: cámara local (índice 0).
- **RTSP**: ingrese la URL manualmente. No se guarda en disco y siempre se
  muestra redactada.

## Problemas frecuentes

| Problema | Solución |
|---|---|
| `FINAL_STATUS: BLOCKED` | Corrija el requisito indicado por preflight. |
| `PYTHON_312_REQUIRED` | Instale Python 3.12.x y vuelva a intentar. |
| `MODEL_MISSING` | Coloque `models/yolo11n.pt` en la carpeta. |
| `MODEL_HASH_MISMATCH` | El modelo no es el esperado; reemplace el archivo. |
| `BLOCKED_BY_DEPENDENCY` | Revise el mensaje de `pip` en el log. |
| La ventana no abre | Ejecute `install\diagnose.ps1` y revise `IMPORTS`. |
| La webcam no responde | Verifique que la cámara esté libre y conectada. |

## Actualización

Vea `docs/UPDATE_PROCEDURE.md`. Regla: nunca actualizar sobre la
instalación activa sin respaldo.

## Rollback

Vea `install/rollback.md` para restaurar una versión previa.

## Secretos y configuración local

Vea `docs/SECRETS_AND_LOCAL_CONFIG.md`. Nunca versionar credenciales ni
`config/local.*`.

## Verificación del paquete

```powershell
powershell.exe -ExecutionPolicy Bypass -File install\verify_package.ps1
```

Confirma MANIFEST, modelo, hash, requirements y exclusiones sin ejecutar el
código principal.
