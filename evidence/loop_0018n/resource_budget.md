# LOOP-0018N — RESOURCE_BUDGET (PASO 8)

## Máquina actual (medido 2026-08-16)

| Recurso | Valor |
|---|---|
| CPU | Intel Core Ultra 7 155H, 16 cores / 22 threads |
| RAM | 15.4 GB |
| GPU | Intel Arc Graphics, 2.0 GB VRAM nominal |
| YOLO11n 640x480 CPU | **54.5 ms/frame** (medido) |
| RAM por cámara + pipeline (LOOP-0018L, 1 cam) | 518–531 MB estable |
| Stream físico certificado | CAM07 subtype0 1280x720@15fps |

## Implicaciones del presupuesto (medido)

- **YOLO continuo a 15 fps:** 54.5 ms × 15 = 0.82 → una sola cámara consume ~82%
  del presupuesto de un núcleo. Detección continua a 15 fps en 4 cámaras es
  **INVIABLE en CPU**.
- **YOLO continuo a 10 fps:** 0.55 → una cámara ~55% de un núcleo; aún no escala a 4.
- Conclusión: la detección YOLO debe ser **config-driven y con frame budgeting**
  (no en todos los frames de todas las cámaras).

## Políticas propuestas (NO hardcodeadas; dependen de medición)

| Modo | Captura | Inferencia YOLO | Uso |
|---|---|---|---|
| QUALITY | subtype0 (main) | alta frecuencia (ej. 1 de 1) | cámara enfocada |
| BALANCED | captura continua | adaptativa (ej. 1 de 2-3) | visión general |
| ECONOMY | substream (subtype1) + frame budget | baja frecuencia (ej. 1 de 5) | grid/thumbnail |

- La selección de subtype por perfil corresponde al motor E-05 (REUSABLE_WITH_ADAPTATION).
- El frame budgeting es parte del diseño de PerCameraDetection.
- No se hardcodea política sin medición por cámara real (trigger: certificación física 4-cam).

## Nota GPU
- `config/default.json` fija `"device": "cpu"`. La GPU Intel Arc existe pero NO está
  habilitada para YOLO. Habilitarla es una decisión futura (no de este LOOP; no toca E-01/OpenCV).