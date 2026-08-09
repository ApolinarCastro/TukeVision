# Secretos y configuración local

Este documento explica qué no debe versionarse, cómo introducir RTSP
manualmente y qué archivos locales deben excluirse.

## Qué no debe versionarse

Nunca empaquetar ni subir a Git:

- Credenciales RTSP (`rtsp://usuario:clave@host/stream`).
- Contraseñas.
- Tokens o claves de API.
- IPs privadas sensibles de cámaras o infraestructura.
- Cualquier archivo `.env`, `.env.*`, `config/local.*` o `config/secrets.*`.

## Cómo introducir RTSP manualmente

La interfaz operativa local (`scripts/run_interface.py`) permite seleccionar
la fuente RTSP dentro de la aplicación. La URL se ingresa en el cuadro de
texto en tiempo de ejecución:

- No se guarda en ningún archivo de configuración.
- No se persiste entre sesiones.
- No se muestra en pantalla: los metadatos siempre la redactan a
  `rtsp://[redacted]`.

No es necesario crear `config/local.json` para RTSP.

## Archivos locales que deben excluirse

El `.gitignore` ya excluye:

```gitignore
.env
.env.*
config/local.*
config/secrets.*
```

Si en el futuro se necesitara una configuración local (por ejemplo, zona o
cámara específica de una instalación), debe crear `config/local.json` y
nunca versionarlo.

## Regla

Ningún secreto ni configuración local debe llegar al paquete portable
generado por `install/package.ps1`. Si se detecta que un archivo excluido
fue empaquetado, no distribuya el paquete y corrija el script de
empaquetado.
