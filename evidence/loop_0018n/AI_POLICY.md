# LOOP-0018N — AI_POLICY (PASO 10)

## Principios

- **CV_DETERMINISTIC_CORE:** detección, tracking, zonas, tiempos, trayectorias.
  Resultados deterministas y verificables. Es la fuente de verdad física.
- **AI_REASONING_LAYER:** análisis de eventos candidatos, explicación, priorización.
  Capa opcional, posterior al evento, NUNCA reemplaza evidencia física.
- AI nunca debe **reemplazar** evidencia física.
- AI nunca debe **inventar** identidad ni evento.
- **UNKNOWN es un resultado válido** (el sistema no debe alucinar).

## Arquitectura

```text
deterministic event
  -> evidence package   (frames, metadata, trayectoria, zona, tiempos — inmutable, DEC-0007)
  -> optional AI second opinion  (explicación, priorización, confianza)
  -> explanation/confidence
  -> operator           (revisión humana, DEC-0011/0012)
```

- El paquete de evidencia se construye SIEMPRE por la capa determinista.
- La opinión de IA es un *candidato*, nunca un veredicto.
- El operador confirma o descarta (DEC-0011/0012).
- Sin IA → el flujo determinista sigue funcionando íntegro.

## Coherencia con TES
- Coherente con `ARCHITECTURE.md` #14 (IA puede explicar/resumir; NO modifica reglas ni confirma incidentes).
- Coherente con DEC-0011/0012 (revisión humana) y DEC-0019 (no infiere intenciones).
- Rechaza explícitamente: identificación facial (DEC-0013), modelos conversacionales
  instalados localmente (Qwen REJECTED en TES).

## Estado
- AI_POLICY definido. Solo especificación.