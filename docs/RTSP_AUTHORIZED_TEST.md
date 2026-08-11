# RTSP Connection Test — Prueba autorizada de conexión RTSP (LOOP-0012A)

Documenta cómo validar, desde un PC autorizado, una fuente RTSP conocida
antes de ejecutar TukeVision. Esta prueba es una extensión del paquete
portable; no es el piloto UC-001 ni una integración completa con Dahua.

La prueba depende de RTSP genérico (no de una marca). Aunque el caso
actual sea Dahua, el diagnóstico es válido para cualquier fuente RTSP.

## Propósito

Verificar, en etapas separadas, que una fuente RTSP autorizada entrega
fotogramas:

```
NETWORK CONNECTIVITY -> RTSP OPEN -> AUTHENTICATION -> VIDEO FRAMES
```

Un fallo se localiza en una etapa concreta; no se devuelve únicamente
`CONNECTION FAILED` sin clasificación.

## Prerrequisitos

- Paquete portable de TukeVision instalado (ver `docs/INSTALL_WINDOWS.md`).
- Preflight superado (`install/preflight.ps1`).
- Diagnóstico del entorno superado (`install/diagnose.ps1`).
- Parámetros RTSP **autorizados por el administrador del equipo**:
  IP/host, puerto, usuario, contraseña, canal y tipo de stream.

## Reglas de seguridad

- Este diagnóstico **no** descubre dispositivos, no escanea red, no
  enumera canales, no prueba credenciales ni contraseñas por defecto.
- La URL RTSP se introduce **manualmente** por el operador autorizado.
- Las credenciales existen únicamente durante la ejecución. No se
  guardan en `config/`, `logs/`, JSON, MANIFEST, README, historial,
  Vault ni `data/evidence/`.
- La contraseña se solicita de forma interactiva y segura (`getpass`);
  nunca se imprime.
- Cualquier log redacta la URL a `rtsp://REDACTED:REDACTED@host/...`.
- El puerto es entrada manual; no se asume `554`.

## Cómo ejecutar la prueba

Desde la raíz del paquete portable:

```powershell
.\.venv\Scripts\python.exe scripts\test_rtsp_connection.py "rtsp://usuario:clave@host:puerto/ruta"
```

O con contraseña interactiva (no se muestra en pantalla ni en historial):

```powershell
.\.venv\Scripts\python.exe scripts\test_rtsp_connection.py --host "rtsp://host:puerto/ruta" --username usuario
```

### Parámetros opcionales

| Parámetro | Default | Descripción |
|---|---|---|
| `--timeout SEC` | 15 | Límite total de la prueba en segundos |
| `--max-frames N` | 30 | Máximo de fotogramas a leer |

## Significado de los estados

| Estado | Significado |
|---|---|
| `NETWORK_UNKNOWN` | No se pudo confirmar la conectividad de red |
| `NETWORK_REACHABLE` | La red respondió |
| `STREAM_OPENED` | La fuente RTSP se abrió |
| `STREAM_OPEN_FAILED` | No se pudo abrir la fuente (clasificación prudente; no se afirma la causa exacta) |
| `NO_FRAMES` | La fuente se abrió pero no entregó fotogramas |
| `FRAMES_RECEIVED` | Se recibieron fotogramas |
| `TIMEOUT` | Se alcanzó el límite de duración |
| `SOURCE_CLOSED` | La fuente se cerró correctamente |

`ERROR_CATEGORY` usa `UNKNOWN_CONNECTION_FAILURE` cuando el backend no
permite distinguir la causa; no se inventa la causa raíz (en particular,
no se reporta `AUTHENTICATION_FAILED` sin evidencia).

## Cómo ejecutar TukeVision después de un PASS

Un `RESULT: PASS` confirma recepción de fotogramas. No ejecuta YOLO,
ByteTrack ni el pipeline automáticamente.

Para ejecutar TukeVision sobre la fuente autorizada (paso manual y
posterior):

```powershell
.\.venv\Scripts\python.exe scripts\run_interface.py
```

Dentro de la interfaz, seleccionar la fuente RTSP e introducir la URL
autorizada. El pipeline certificado procesará los fotogramas.

## Cómo detener

- La prueba finaliza sola por límite de tiempo o de fotogramas.
- En la interfaz, usar el botón **Detener** o cerrar la ventana; el
  pipeline se cierra limpiamente (no se fuerza el proceso).

## Manejo de credenciales

- Solo existen en memoria durante la ejecución.
- No se persisten, loguean ni muestran.
- El resultado del diagnóstico nunca incluye `password`, la URL original
  con credenciales ni la IP privada.

## Solución de problemas

| Síntoma | Acción |
|---|---|
| `STREAM_OPEN_FAILED` | Verificar IP/puerto y que el equipo permita RTSP saliente |
| `NO_FRAMES` | Verificar canal, tipo de stream y codec con el administrador |
| `TIMEOUT` | Aumentar `--timeout` con moderación o revisar red |
| `NETWORK_UNKNOWN` | Confirmar conectividad con el administrador |

## Limitaciones

- Este diagnóstico NO ejecuta detección ni negocio.
- `RESULT: PASS` NO certifica UC-001.
- `HTTP` accesible ≠ `RTSP` validado.
- `RTSP frames recibidos` ≠ `UC-001 validado`.
- El paquete portable preparado ≠ despliegue de producción.
