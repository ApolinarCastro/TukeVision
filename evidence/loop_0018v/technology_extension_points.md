# Technology extension points after LOOP-0018V

Checkpoint contra Playbook/Radar TES. No se adoptó tecnología externa.

| Seam | Opción futura | Límite |
|---|---|---|
| `InferenceEngine` | OpenVINO/ONNX/YOLO alternatives | Gap medido; adapter + paridad |
| `LocalTracker` | ByteTrackTracker/BoT-SORT | Gap local; identidad por cámara |
| Observation/TemporalActivity | Pose/action references | Use case + goldens; sin conclusión criminal |
| `evidence_ref` | EvidenceBackend/index | Necesidad aprobada; contrato estable |
| SourceManager snapshot | go2rtc/PyAV | Gap RTSP; loop separado; E-01 intacto |
| Track+time+topology+evidence | trajectory graph | Próximo candidato; no iniciado |
| Ninguno | ReID/face | Bloqueado; `PRESERVED_DISABLED` |

Clasificación no implica adopción (DEC-0029/0037). `NEW_DEPENDENCIES=0`.
