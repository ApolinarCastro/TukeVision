# Procedimiento de actualización

Regla inicial:

> NO actualizar sobre la instalación activa sin respaldo.

## Flujo

### 1. Respaldo

- Detenga TukeVision.
- Copie `data/evidence/` y cualquier configuración local a un lugar seguro.
- Copie (o renombre) la instalación activa a `TukeVision_backup_YYYYMMDD`.

### 2. Nueva carpeta

- Descomprima el nuevo paquete portable en una carpeta nueva, por ejemplo
  `TukeVision_new`.
- No instale sobre la carpeta activa.

### 3. Instalar

```powershell
powershell.exe -ExecutionPolicy Bypass -File install\preflight.ps1
powershell.exe -ExecutionPolicy Bypass -File install\install.ps1
```

### 4. Diagnosticar

```powershell
powershell.exe -ExecutionPolicy Bypass -File install\diagnose.ps1
```

Confirme: `IMPORTS: OK`, `MODEL_HASH_VALID: YES`, `DIAGNOSE_STATUS: COMPLETED`.

### 5. Probar

- Inicie la interfaz y verifique que abre y cierra correctamente.
- Si tiene una fuente autorizada, haga una prueba corta.

### 6. Cambiar acceso

- Cuando la nueva carpeta funcione, renombre la activa a `_old` y la nueva
  a `TukeVision`.
- Actualice cualquier acceso directo que apunte a la ruta.
- Conserve el respaldo hasta confirmar estabilidad.

## Reglas

- La evidencia de `data/evidence/` nunca se borra automáticamente.
- No actualizar sobre la instalación activa sin respaldo.
- No se automatiza el proceso de cambio de acceso en esta etapa.
