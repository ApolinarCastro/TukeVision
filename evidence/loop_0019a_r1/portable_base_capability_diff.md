# LOOP-0019A-R1 — portable ↔ BASE capability diff

| Capacidad | Portable | BASE | Resultado |
|---|---|---|---|
| 4 fuentes RTSP / SourceManager | Existe | Existe | Reutilizable |
| AdvanceChain (actividad → inferencia → tracker → correlación → behavior → evidencia) | Existe | Existe | Núcleo protegido presente |
| YOLO/inferencia | Existe | Existe, config `yolo` | Existe en runtime |
| LocalTrack / Track ID | Existe | Existe | Se produce internamente |
| Correlación/trajectory | Existe | Existe | Se produce internamente |
| BehaviorSignal/RiskEvent | Existe | Existe | Se evalúa internamente |
| Evidencia persistente | Existe | Existe | Se enlaza internamente |
| Entrypoint `TukeVision.bat` multicámara | No | Sí | BASE-only, pendiente de reconciliar |
| 2×2 multicámara | UI base no dedicada | Sí | Visible, pero sólo frame/estado |
| Overlay detección/tracking/zonas/eventos | No verificable en portable | No conectado al panel multicámara | Gap de presentación |
| Panel lateral coherente multicámara | No | No: conserva estado legacy FILE | Gap de presentación |

El portable es un paquete histórico y no contiene los cambios de entrada multicámara actuales; no se usa como fuente para recuperar credenciales ni configuración secreta.
