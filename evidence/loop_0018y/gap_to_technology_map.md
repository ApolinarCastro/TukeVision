# LOOP-0018Y gap-to-technology map

Existing TES Technology Radar and Technology Ingestion Playbook were consulted only after empirical gap classification.

| GAP | CANDIDATE | EXPECTED_INFORMATION_GAIN | CURRENT_EXTENSION_POINT | LICENSE_STATUS | DATA_REQUIREMENT | COMPUTE_REQUIREMENT | GOVERNANCE | NEXT_ACTION |
|---|---|---|---|---|---|---|---|---|
| GAP-001 signal review data | internal bounded review exporter | exposes existing rule/feature/evidence facts | `BehaviorResult` consumer | internal | existing outputs only | negligible | non-accusatory labels | next validation design; no ingestion |
| GAP-002 rule combination | existing config/risk diagnostics | determines which signals fail to combine | BehaviorEngine config | internal | reviewed signal sample | negligible | no tuning in this loop | collect evidence first |
| GAP-003 evidence sampling | existing PersistentEvidence policy | quantifies selected frames without event | EvidencePersistence | internal | retained metadata | negligible | bounded retention | analyze in later review workflow |
| Object interaction | RetailS/TheftGuard patterns | potentially adds interaction context | future BehavioralEventBackend | mixed/not revalidated here | labeled authorized clips | additional inference | privacy/taxonomy review | NOT_JUSTIFIED_BY_CURRENT_EVIDENCE |
| Pose/action | pose/action radar candidates | potentially adds action context | future BehavioralEventBackend | not revalidated here | labeled authorized clips | material | privacy/taxonomy review | NOT_JUSTIFIED_BY_CURRENT_EVIDENCE |
| Inference optimization | OpenVINO | may reduce CPU | InferenceEngine adapter | recorded candidate | comparable benchmark | platform-specific | compliant if isolated | NOT_JUSTIFIED; measured process peak was ~34.2% of 22 logical processors |

`EXTERNAL_TECHNOLOGY_INGESTED=NO`. No empirical P0/P1 gap justifies an external technology in this loop.
