# LOOP-0018N — ACTIVITY_LAYER_SPEC (PASO 9)

## Propósito

Formalizar la Activity Intelligence Layer reutilizando lo existente
(Detection → Track → Trajectory → Zone → Interaction → Activity → Event).
Solo especificación: NO implementación en este LOOP.

## Cadena de transformación

```text
Detection -> Track -> Trajectory -> Zone -> Interaction -> Activity -> Event
  (YOLO)     (BT)     (E-02)       (Zone)  (nuevo)      (nuevo)   (motor)
```

- **Determinista:** detección, tracking, zonas, tiempos, trayectorias, transiciones de zona.
- **Interaction/Activity:** calculadas a partir de la trayectoria + geometría (derivadas de
  datos objetivos), sin inferir intención (DEC-0019).

## Primera taxonomía permitida

| Actividad | Definición (objetiva, derivada) |
|---|---|
| ENTER_ZONE | transición zona fuera→dentro (ya soportado por Zone.update) |
| EXIT_ZONE | transición zona dentro→fuera |
| DWELL | permanencia continua en zona ≥ umbral |
| LOITERING | DWELL prolongado + movimiento mínimo (varianza de trayectoria baja) |
| APPROACH_PRODUCT | trayectoria converge hacia un producto/área de interés |
| WATCH_PRODUCT | APPROACH + permanencia localizada estable |
| TOUCH_PRODUCT | intersección track↔borde de producto (proximidad) |
| RETURN_PRODUCT | TOUCH + alejamiento (no consume para TOUCH + RELEASE) |
| MOVE_BETWEEN_ZONES | secuencia de zona A→B registrada |

## Regla crítica

- **NO etiquetar THEFT/ROBBERY como hecho determinista.**
- TOUCH/RETURN/APPROACH son candidatos; el incidente (robo) es un RIESGO/CANDIDATO
  sujeto a evidencia y revisión humana (DEC-0011/0012).
- La Activity Layer produce *actividades observadas*, nunca *intenciones* (DEC-0019).

## Dependencias
- Trajectory (E-02) para historia de posiciones.
- Zone/Dwell/Flow existentes.
- Productos como zonas/áreas de interés (extensión del modelo Zone).

## Estado
- ACTIVITY_LAYER_SPEC_COMPLETE = PASS (G7). DISEÑADO, no implementado.