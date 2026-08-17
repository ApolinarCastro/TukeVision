# LOOP-0018Z reuse check

| Capability | Classification | Reuse decision |
|---|---|---|
| BehaviorSignal/BehaviorFeature serialization | REUSE_WITH_ADAPTATION | consume existing immutable `to_dict` contracts; do not alter BehaviorEngine |
| Secret redaction | ALREADY_EXISTS | reuse `redact_rtsp_url` through existing behavior serialization |
| Evidence references and SHA verification | ALREADY_EXISTS | reuse `PersistentEvidenceStore.verify/resolve` |
| Atomic file replacement | REUSE_WITH_ADAPTATION | follow `PersistentEvidenceStore` temp-file + `os.replace` pattern |
| JSONL/CSV review export | MISSING | implement minimal stdlib JSONL only |
| Bounded balanced signal sampler | MISSING | implement deterministic bounded candidate buffer and balanced selection |
| Human classification enum | MISSING | implement controlled review vocabulary |
| Human review database/dashboard | MISSING_AND_OUT_OF_SCOPE | do not build |

TES QW-00 explicitly authorizes an internal minimal capability because the external alternatives solve perception or platforms, not this observability gap. No dependency is required.
