# LOOP-0009 — Desviación de implementación

## Hecho

El plan establecía utilizar Tkinter si estaba disponible.

La ejecución implementó la ventana principal con OpenCV.

## Autorización

El cambio no fue solicitado ni aprobado por el usuario.

## Clasificación

EXECUTION_DEVIATION

## Corrección

LOOP-0009C restauró el diseño aprobado utilizando Tkinter.

## Impacto

Evidencia real después de auditoría (LOOP-0009C, 2026-08-09):

- `TKINTER_AVAILABLE: YES` (Tk 8.6) — verificado con
  `python -c "import tkinter"`.
- `OPENCV_UI_DECISION_APPROVED_BY_USER: NO` — no hay evidencia de
  autorización para sustituir Tkinter por OpenCV como tecnología principal
  de interfaz.
- `PIPELINE_OUTPUT_EQUIVALENCE: PASS` — el hook `on_frame` no altera los
  resultados del pipeline (RUN A vs RUN B idénticos).
- `UNAPPROVED_UI_PROJECTION_REMOVED: YES` — se eliminó `level_for_duration()`
  de `src/risk/calculator.py`; el archivo quedó exactamente en su estado
  certificado previo.
- `DEPENDENCIES_CHANGED: NO` — no se modificaron `requirements.txt` ni
  `requirements.lock.txt`; la conversión de frames a `PhotoImage` usa
  `cv2.imencode` (PNG) sin introducir Pillow como dependencia.
- `BUSINESS_LOGIC_CHANGED: NO`.

## Regla aprendida

Una implementación no puede sustituir una tecnología explícitamente indicada
en el plan sin detenerse y solicitar autorización.
