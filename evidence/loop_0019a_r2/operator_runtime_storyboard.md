# LOOP-0019A-R2 — tesis visual y storyboard técnico

Aplicación de `manim-video` como documentación de arquitectura; no se integra
Manim al producto ni se genera una capacidad nueva.

## Tesis visual

Una única cadena operacional ya producía datos reales; el wrapper de
presentación los interpretaba y retenía incorrectamente.

## Escenas

1. **Cadena real** — revelar progresivamente BAT → pipeline → YOLO → temporal →
   behavior → evidencia. Prueba: no existe un segundo pipeline.
2. **Pérdida en frontera** — los resultados alcanzan `EVIDENCE_RETURNED` y se
   apagan al entrar a `UI_MODEL_RECEIVED`. Prueba: primer punto roto.
3. **Reparación quirúrgica** — reemplazar sólo el adaptador y separar frame
   latest-wins de analítica sparse. Prueba: el core permanece congelado.
4. **Gate humano** — cuatro paneles, estados reales, STOP y evidencia; G1–G10
   quedan en manos del operador.

## Plan de render

Formato previsto si se solicitara posteriormente: 16:9, cuatro escenas,
revelado progresivo, smoke `-ql` y luego MP4/thumbnail. Render no ejecutado en
R2 porque el objetivo es reparación de producto y las capacidades nuevas están
congeladas.
