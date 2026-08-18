# LOOP-0019A-R2 Addendum V1 — validación técnica

## Alcance

- QW-04: congelado.
- Capacidades nuevas: congeladas.
- Pipeline backend: no reimplementado.
- Cambios preexistentes de otros loops: preservados.

## Reparaciones de representación

1. El resultado canónico conserva un máximo de 16 cajas reales y la caja
   primaria utilizada por el contrato espacial existente del tracker.
2. La vista 2×2 presenta detección, track, evento, frame analítico, temporal,
   behavior, riesgo y evidencia sin fabricar valores.
3. Una caja analítica sólo se dibuja cuando su índice coincide con el frame de
   video presentado. Esto impide superponer geometría antigua sobre una imagen
   más nueva.
4. El panel expone por separado el índice de video y el índice analítico.
5. Los cuatro canales usan el stream principal de forma coherente y el
   renderer conserva aspecto sin upscaling.

## Credenciales

- El host se obtiene únicamente como metadata de endpoint no secreta.
- Usuario y contraseña se solicitan de nuevo mediante `getpass` local.
- No se recupera el usuario desde evidencia histórica.
- No se imprime ni persiste ninguna credencial.

## Gates técnicos

- RED de fidelidad visual: confirmó geometría del frame 9 dibujada sobre el
  frame 10 antes de la corrección.
- GREEN focalizado UI: 17 tests, PASS.
- GREEN ampliado UI/cadena/inferencia/tracking: 103 tests, PASS.
- Regresión completa final: 434 tests, PASS, 4 skips de backend opcional.
- Carrera de fixture observada una vez en `test_start_health_snapshot`:
  repetición aislada 2/2 PASS y segunda regresión completa PASS.
- `compileall`: PASS.
- Escaneo de secretos: 4 PASS, 0 FAIL.
- `git diff --check`: PASS (sólo avisos de normalización LF/CRLF).

## Gate físico

`TukeVision.bat` se lanzó en terminal visible con credenciales frescas
solicitadas mediante `getpass`.

- RUN_ID: `RUN-A2308F`.
- Las cuatro fuentes fueron registradas.
- CAM-001: fallo de apertura RTSP.
- CAM-002: fallo de apertura RTSP.
- CAM-003: fallo de apertura RTSP.
- CAM-004: fallo de apertura RTSP.
- Frames recibidos por cámara: 0.
- Inferencias ejecutadas por cámara: 0.
- Evidencia nueva producida: 0.
- Runtime y terminal: cerrados.

`AUTHORIZED_SOURCE_UNAVAILABLE`

La causa externa concreta no puede distinguirse entre autenticación rechazada,
endpoint no alcanzable o incompatibilidad del stream sin una fuente accesible.
Por instrucción del operador se ejecutó STOP sin cambios posteriores de código,
thresholds ni configuración. G1–G10 no se autoaprueban.

## Recertificación física RUN-251B32

Tras reconectar las fuentes, el operador volvió a introducir credenciales
frescas mediante `getpass` y ejecutó el entrypoint oficial.

- Fuentes activas: 4/4, sin `SOURCE_FAILED`.
- Observaciones: CAM-001=37, CAM-002=36, CAM-003=55, CAM-004=64 en la lectura
  intermedia.
- CAM-003 produjo 28 eventos `PERSON_DETECTED` en la lectura intermedia.
- Evidencia nueva: 256 archivos, 64 por cámara.
- Cierre final: 32 eventos, 24 tracks iniciados, 8 actualizaciones, 24
  actividades y 0 errores de inferencia.

Evidencia humana de la UI detenida:

- G1 cuatro cámaras: PASS.
- G2 calidad/layout: PASS.
- G3 detección: PARTIAL; evento visible, caja no persistente sobre el frame
  analítico correspondiente.
- G4 tracking: PARTIAL; Track ID visible, asociación gráfica no persistente.
- G5 temporal: PASS.
- G6 eventos: PASS.
- G7 behavior: PASS (`REPEATED_ACTIVITY` visible).
- G8 evidencia: PASS; `Abrir evidencia` abrió `data/runtime_evidence` con las
  carpetas CAM-001..CAM-004.
- G9 coherencia UI: PASS.
- G10 detener: PASS; las cuatro fuentes y la cadena cerraron limpiamente.

La captura demuestra la divergencia restante: CAM-003 mostraba video frame 556
y analítica frame 544. La UI evitó correctamente dibujar geometría antigua
sobre el frame 556, pero no conservó el frame 544 para revisión, dejando G3/G4
sin verificación visual suficiente.

## Reparación final exact-frame

- Se conserva un solo frame analítico bounded por cámara cuando existe
  geometría real de evento/track.
- La UI lo etiqueta `Imagen: ANALITICA <frame>` y declara por separado
  `Video: <frame vivo>`.
- Las cajas YOLO y Track ID sólo se dibujan sobre el índice analítico exacto.
- No se modificaron YOLO, thresholds, reglas conductuales, QW-04 ni evidencia.
- Tests focalizados: 18 PASS.
- Regresión final: 435 PASS, 4 skips de backend opcional.
- `compileall`: PASS.
- Secret scan: 4 PASS, 0 FAIL.
- `git diff --check`: PASS, con avisos LF/CRLF preexistentes.

## Certificación final RUN-ADD3A1

Las capturas aportadas por el operador demuestran cajas YOLO y Track ID sobre
frames `ANALITICA` exactos en CAM-003 y CAM-001, incluyendo situaciones donde
el video vivo avanzó y la imagen analítica quedó explícitamente diferenciada.

Traza final bounded:

- CAM-001: 1501 frames, 1 detección, 1 track, 1 temporal, 208 evidencias.
- CAM-002: 2017 frames, 0 detecciones, 272 evidencias.
- CAM-003: 1555 frames, 117 detecciones, 116 tracks, 116 temporales, 13
  señales de behavior y 215 evidencias.
- CAM-004: 1220 frames, 0 detecciones, 164 evidencias.
- Cierre agregado: 117 eventos, 78 tracks iniciados, 39 actualizaciones,
  78 actividades, 0 errores de tracking y 0 errores de inferencia.
- Las cuatro fuentes terminaron y `SourceManager` cerró limpiamente.
- Ventana, procesos Python y terminal aislada: cerrados; 0 instancias activas.

Matriz final:

- G1 FOUR_CAMERA_VIEW: PASS.
- G2 IMAGE_QUALITY: PASS.
- G3 YOLO_DETECTION: PASS.
- G4 TRACKING: PASS.
- G5 TEMPORAL: PASS.
- G6 EVENTS: PASS.
- G7 BEHAVIOR: PASS.
- G8 EVIDENCE: PASS.
- G9 UI_COHERENCE: PASS.
- G10 STOP_CONTROL: PASS.

`OPERATOR_VERIFICATION = PASS`

`PRODUCT_CAPABILITY_STATUS = FUNCTIONAL_TECHNICAL_INTEGRATED_OPERATOR_PASS`
