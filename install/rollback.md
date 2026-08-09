# Rollback de una instalación TukeVision

Procedimiento simple para restaurar una versión previa en caso de que una
instalación o actualización falle.

## Cuándo usar este procedimiento

- La instalación dejó la aplicación en estado incorrecto.
- Una actualización rompió el arranque.
- Se detectó corrupción en `.venv` o dependencias.

## Procedimiento

### 1. Detener TukeVision

Cierre la interfaz (`start_tukevision.ps1`) y cualquier proceso Python
relacionado. Verifique que no queden procesos activos.

### 2. Conservar la evidencia

La carpeta `data/evidence/` es de solo lectura operativa:

- No se borra automáticamente en instalación ni actualización.
- Antes de cualquier rollback, haga una copia de `data/evidence/` a un
  lugar seguro fuera de la instalación.

```powershell
Copy-Item -Recurse -Force "data\evidence" "C:\respaldo\evidence_backup"
```

### 3. Renombrar la instalación actual

No la elimine de inmediato. Renombre la carpeta para poder volver a ella.

```powershell
# Dentro del directorio padre de TukeVision
Rename-Item "TukeVision" "TukeVision_old_failed"
```

### 4. Restaurar la versión previa

- Si conserva el respaldo de la instalación anterior, cópiela al nombre
  original `TukeVision`.
- Si usa el paquete portable, descomprímalo en `TukeVision` y ejecute la
  instalación:

```powershell
powershell.exe -ExecutionPolicy Bypass -File install\preflight.ps1
powershell.exe -ExecutionPolicy Bypass -File install\install.ps1
```

### 5. Ejecutar el diagnóstico

```powershell
powershell.exe -ExecutionPolicy Bypass -File install\diagnose.ps1
```

Revise que `IMPORTS: OK`, `MODEL_HASH_VALID: YES` y `VENV_STATUS: PRESENT`.

### 6. Validar

Inicie la interfaz y confirme que abre y cierra correctamente:

```powershell
powershell.exe -ExecutionPolicy Bypass -File start_tukevision.ps1
```

## Notas

- No se crea un sistema automático de rollback en esta etapa.
- No borre `TukeVision_old_failed` hasta confirmar que la versión restaurada
  funciona correctamente.
- La evidencia de `data/evidence/` debe permanecer siempre fuera de
  cualquier limpieza automática.
