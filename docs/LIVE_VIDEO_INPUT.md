# Entrada de video en vivo (webcam / RTSP)

Extensión del núcleo certificado SPEC-0001 (`cf876a9`) para aceptar fuentes
de video en vivo. No modifica la lógica de negocio ni la certificación:
el núcleo de detección, seguimiento y eventos sigue siendo el mismo.

## Fuentes soportadas

| Fuente       | Clase               | `source_type` | `is_live` |
|--------------|---------------------|---------------|-----------|
| Archivo      | `VideoSource`       | `FILE`        | `False`   |
| Webcam local | `WebcamSource`      | `WEBCAM`      | `True`    |
| RTSP         | `RTSPSource`        | `RTSP`        | `True`    |

Todas implementan la misma interfaz común:

```
open() -> VideoMetadata
read() -> Optional[Tuple[int, MatLike]]
frames() -> Generator[Tuple[int, MatLike], None, None]
close()
metadata -> Optional[VideoMetadata]
is_open -> bool
source_type -> str
is_live -> bool
```

`VideoMetadata` ahora incluye `source_type` (default `"FILE"`).

## Uso

### Webcam local

```python
from src.capture.live_sources import WebcamSource

with WebcamSource(camera_index=0, backend=cv2.CAP_DSHOW) as source:
    for frame_index, frame in source.frames():
        ...
```

En Windows es recomendable indicar el backend (`CAP_DSHOW`) porque el backend
por defecto puede bloquearse si la cámara no responde.

### RTSP

La URL se recibe externamente (argumento o variable de entorno), nunca se
almacena en código ni configuración versionada:

```python
from src.capture.live_sources import RTSPSource

source = RTSPSource(rtsp_url="rtsp://user:pass@host/stream")
metadata = source.open()
```

Los metadatos redactan siempre la URL a `rtsp://[redacted]` para no exponer
credenciales.

### Pipeline

```python
from src.app.pipeline import Pipeline, load_config
from src.capture.live_sources import WebcamSource

pipeline = Pipeline(config=load_config())
with WebcamSource(camera_index=0) as source:
    summary = pipeline.process_source(source)
```

`Pipeline.process(video_path)` sigue disponible y ahora delega en
`process_source(VideoSource(video_path))`.

## Diferencia de tiempo en fuentes en vivo

En video de archivo los tiempos de permanencia se calculan desde el índice de
fotograma y el FPS del archivo. En fuentes en vivo el reloj es
`time.monotonic()`:

- `_live_timestamp()` genera marcas de tiempo ISO con la hora del sistema.
- Las permanencias se calculan sobre tiempo transcurrido real.
- Se usa `fps = 1.0` (tiempo de reloj, no tiempo por fotograma).

## Política de reconexión RTSP

Mínima y acotada para evitar bucles infinitos:

- `max_reconnect_attempts` (default `3`): límite global de reconexiones en
  toda la vida de la fuente.
- `reconnect_delay_seconds` (default `2.0`): espera entre intentos.
- Si se agotan los reintentos, la fuente termina en estado `FAILED`.

## Seguridad de credenciales

- La URL RTSP se pasa como argumento o variable de entorno
  (`TUKEVISION_RTSP_URL`).
- No hay URLs, usuarios ni contraseñas en código, tests, configuración
  versionada ni documentación del repositorio.
- Los metadatos redactan la ruta a `rtsp://[redacted]`.

## Scripts de inspección

```powershell
python scripts/inspect_webcam.py 0
python scripts/inspect_rtsp.py  # o $env:TUKEVISION_RTSP_URL
```

## Limitaciones

- Una sola fuente a la vez.
- Ancho máximo 640 px (reducción si es mayor).
- Sin reconocimiento facial ni análisis de identidad.
- Sin autenticación contra la cámara; solo la conexión RTSP.
- La validación operacional de un caso de negocio es un paso separado
  (requiere video operacional autorizado; el video de certificación
  `data/input/Video.mp4` no sirve para ello).
