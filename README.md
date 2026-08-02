# TukeVision

Prototipo local para transformar video en observaciones, eventos, riesgo, alertas y evidencia trazable.

## Estado

Implementación del primer prototipo funcional (SPEC-0001) completada a nivel de módulos. Pendiente de ejecutar la prueba integral con un video real.

## Requisitos

- Windows.
- Python 3.12.9 (64 bits).
- Entorno virtual en `.venv`.

## Activar el entorno virtual

```powershell
Set-Location "D:\TukeVision"
.\.venv\Scripts\Activate.ps1
```

## Ejecutar el prototipo

Coloque un video local en `data/input/` y ejecute:

```powershell
.\.venv\Scripts\python.exe scripts\run_prototype.py "data\input\video.mp4"
```

### Estructura de entrada y salida

```text
data/input/        Video local a procesar (uno a la vez).
data/output/       Video procesado con anotaciones (processed.mp4).
data/evidence/     Evidencia por alerta: frame.jpg y metadata.json.
data/temp/         Archivos temporales (imágenes de prueba).
models/            Peso del modelo yolo11n.pt (no se sube a Git).
config/default.json Configuración: detección, zona, negocio y alertas.
```

### Salida esperada

```text
VIDEO_PATH:
FRAMES_PROCESSED:
PERSONS_DETECTED:
TRACKS_CREATED:
OBSERVATIONS_CREATED:
EVENTS_CREATED:
ALERTS_CREATED:
EVIDENCE_CREATED:
OUTPUT_VIDEO:
FINAL_STATUS:
```

## Significado de las salidas

- `PERSONS_DETECTED`: total de detecciones de personas (puede incluir la misma persona en varios fotogramas).
- `TRACKS_CREATED`: trayectorias temporales únicas asignadas por seguimiento.
- `OBSERVATIONS_CREATED`: hechos objetivos (entrada, permanencia, salida).
- `EVENTS_CREATED`: eventos de permanencia prolongada (más de 30 segundos).
- `ALERTS_CREATED`: alertas generadas cuando el riesgo es 60 o superior.
- `EVIDENCE_CREATED`: carpetas con fotograma y metadatos por alerta.

## Restricciones del prototipo

- Sin reconocimiento facial.
- Sin identificación de personas.
- Sin cámaras en vivo.
- Sin varias cámaras ni varias zonas.
- Sin inteligencia artificial conversacional.
- Sin servicios externos ni base de datos.
- Procesamiento por CPU, un video a la vez.
- Resolución máxima de 640 píxeles de ancho.
- Procesamiento secuencial sin cargar el video completo en memoria.

## Configuración

`config/default.json` permite ajustar:

- Modelo, umbral de confianza y dispositivo de detección.
- Zona poligonal (identificador, nombre y vértices).
- Tienda, cámara y tiempo máximo de permanencia.
- Umbral de riesgo para generar alertas.

## Solución de errores básicos

- `El archivo de video no existe`: verifique que el video esté en `data/input/` y la ruta sea correcta.
- `Modelo no encontrado`: descargue `yolo11n.pt` (modelo YOLO Nano) y colóquelo en `models/`.
- `No se puede abrir el video`: el archivo puede estar dañado o no ser un formato compatible con OpenCV.
- Errores de dependencias: ejecute `python -m pip install -r requirements.txt` dentro de `.venv`.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

## Fuente de especificaciones

Las decisiones y especificaciones oficiales viven en el Vault TES de Obsidian.
