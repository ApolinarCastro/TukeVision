# Interfaz Operativa Local (LOOP-0009 / LOOP-0009C)

Aplicación de escritorio local sobre el núcleo certificado de TukeVision.
No agrega capacidades de detección ni modifica la lógica de negocio: consume
el mismo pipeline y muestra su estado en una sola pantalla.

**Tecnología de interfaz: Tkinter** (biblioteca estándar). OpenCV se mantiene
como tecnología de visión: captura, procesamiento de frames, geometría,
anotaciones y evidencia — NO como sistema de ventanas.

## Ejecutar

```powershell
.\.venv\Scripts\python.exe scripts\run_interface.py
```

No requiere argumentos. La selección de fuente se realiza dentro de la
aplicación:

- **FILE**: botón "Seleccionar archivo" (selector nativo `filedialog`).
- **WEBCAM**: índice de cámara (por defecto `0`); no se escanean cámaras.
- **RTSP**: URL por entrada manual. Tras iniciar se muestra `RTSP: REDACTED`;
  las credenciales nunca se guardan, persisten, loguean ni muestran.

## Qué muestra (una sola pantalla)

| Elemento | Origen |
|---|---|
| Video | Frame anotado del pipeline (zona + cajas) dentro de Tkinter |
| Fuente | `source_type` + ruta (redactada en RTSP) |
| Estado de conexión | `source.state` del `FrameSnapshot` |
| Resolución / FPS | `FrameSnapshot` |
| Zona | polígono dibujado en el video + `zone_id`/`zone_name` en panel |
| Track ID | `followed_track_id()` (prioriza dentro de zona, mayor permanencia) |
| Permanencia | `stays_seconds` del `FrameSnapshot` |
| Riesgo | **solo riesgo real del núcleo**: `latest_alert.risk_score`; si no
  existe, `risk_text` del pipeline; si no hay, `—`. No se proyecta ni calcula |
| Alertas | Alert ID, evento, risk score, hora |
| Evidencia | ruta de la última evidencia; botón "Abrir evidencia" abre la carpeta
  en modo lectura |

## Arquitectura

```
┌─────────────────────────────┐
│         TKINTER UI          │
│  ┌─────────────┐ ┌────────┐ │
│  │   VIDEO     │ │ FUENTE │ │
│  │ (PhotoImage)│ │ TRACK  │ │
│  │             │ │ RIESGO │ │
│  └─────────────┘ └────────┘ │
│  [Seleccionar] [Iniciar] [Detener] [Abrir evidencia] │
└─────────────────────────────┘
```

Separación mínima:

- `src/ui/state.py` — `UiState` (estado de presentación) y helpers puros
  (`followed_track_id`, `redact_source_display`).
- `src/ui/controller.py` — `UiController`: hilo de trabajo ejecuta el
  pipeline; entrega snapshots a la vista mediante `queue.Queue(maxsize=1)`
  con backpressure (se descarta el snapshot visual viejo). Nunca toca widgets.
- `src/ui/tk_view.py` — `TkApp`: widgets; actualiza solo desde el hilo
  principal vía `Tk.after()`. Convierte frames BGR a `PhotoImage` con
  `cv2.imencode(".png")` (sin Pillow).

## Threading y cierre

```
WORKER THREAD → pipeline → queue → MAIN TK THREAD → widgets
```

- Los widgets de Tk solo se modifican desde el hilo principal.
- Backpressure: la cola visual tiene tamaño 1; el negocio no pierde frames,
  la presentación sí puede descartar snapshots visuales.
- Memoria: se conserva solo el frame visual actual, el estado y una lista
  pequeña de alertas/evidencia; no se acumulan arrays ni videos.
- **Detener** o cerrar la ventana: señal de stop → el pipeline termina →
  `source.close()` → el hilo de trabajo termina → la UI cierra. No se usa
  `os._exit()`, kill ni terminación forzada.

## Evidencia

- La UI solo puede abrir la carpeta de evidencia (modo lectura).
- No edita, elimina, renombra ni regenera evidencia.

## Pruebas

- `tests/test_ui_controller.py` — estado inicial, transiciones
  READY→RUNNING→STOPPED, error de fuente, actualización de snapshot, alertas,
  redacción RTSP, señal de stop, backpressure y cierre seguro.
- `tests/test_pipeline_equivalence.py` — RUN A (sin `on_frame`) vs RUN B
  (con `on_frame` no-op): salidas idénticas.
- `tests/test_pipeline_snapshot.py` — el hook `on_frame` entrega
  `FrameSnapshot` por fotograma.

## Validaciones reales (LOOP-0009C)

- `WEBCAM_TKINTER_REAL_TEST: PASS` — webcam índice 0, frames 640x480,
  conexión OPEN, stop limpio (`STOPPED_BY_USER`).
- `FILE_TKINTER_REAL_TEST: PASS` — clip corto de 45 frames, `final_status: OK`.
- `PIPELINE_OUTPUT_EQUIVALENCE: PASS`.
- `SPEC-0001` y `LIVE_INPUT_READY` sin regresión.
