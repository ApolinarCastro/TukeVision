# LOOP-0019A-R1 — precheck

Fecha: 2026-08-17

## Estado reproducible

- HEAD: `b8ebcae309a2a080919889df87f2965c78f32ce5`
- Rama: `product/loop-0018r-temporal-tracking`
- BASE: `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision`
- La rama contiene cambios de trabajo y artefactos de ejecuciones reales; se preservan y no se revierten.
- QW-04 permanece pausado durante esta reconciliación.

## Artefactos y superficies comparadas

- Portable inspeccionable: `dist/TukeVision-portable.zip` (listado directo, sin extraer ni ejecutar).
- BASE inspeccionada: `src/`, `scripts/`, `config/default.json`, `TukeVision.bat`, `start_tukevision.ps1`.
- Evidencia runtime disponible: `evidence/loop_0019a/real_run/`.
- No se modificó TES ni se alteró el baseline de comportamiento.

## Resultado del precheck

El portable contiene `AdvanceChain`, `OperationalPipeline`, detección YOLO, tracking, correlación, comportamiento y UI base, pero no contiene el entrypoint multicámara `scripts/run_multicamera.py`, `TukeVision.bat` ni el modelo de presentación `src/ui/multicamera.py` presentes en BASE. BASE sí tiene el ejecutor multicámara, pero su callback sólo publica frame/estado al modelo visual y descarta el resultado analítico devuelto por `OperationalPipeline`.

Conclusión: se autoriza únicamente una adaptación de presentación/wiring después de documentar la trazabilidad; no hay indicio que justifique reimplementar el núcleo protegido.
