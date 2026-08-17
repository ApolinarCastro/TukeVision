# LOOP-0018X behavior capability requirements

Source: approved loop specification plus the existing TES corpus. No new web research was performed.

| Capability | Classification | Operational interpretation |
|---|---|---|
| Track and activity duration | ALREADY_SUPPORTED | `LocalTrack` and `TemporalActivity` timestamps/duration |
| Detection/event count | ALREADY_SUPPORTED | Bounded event references and counters |
| Evidence references | ALREADY_SUPPORTED | Existing immutable references; no frame duplication |
| Camera transitions and trajectory duration | ALREADY_SUPPORTED | LOOP-0018W topology/trajectory contracts |
| Prolonged dwell | DERIVABLE_WITH_RULES | Deterministic threshold over duration |
| Repeated observations/activity | DERIVABLE_WITH_RULES | Deterministic threshold over event count |
| Multi-camera sequence | DERIVABLE_WITH_RULES | Deterministic threshold over trajectory transitions |
| Zone visits | DERIVABLE_WHEN_METADATA_EXISTS | Only from explicit `zone_visits` metadata; never inferred |
| Pose/action classification | REQUIRES_EXTERNAL_EXTENSION_AND_DATA | Needs model, goldens, licensing and privacy validation |
| Object interaction classification | REQUIRES_EXTERNAL_EXTENSION_AND_DATA | Needs a validated temporal/pose backend |
| Shoplifting recognition | OUT_OF_SCOPE | The product must not infer guilt or intent |
| Identity/ReID/biometrics | GOVERNANCE_BLOCKED | Explicitly prohibited by current decisions |

The P0 need is therefore an explainable deterministic rules layer over existing facts. It does not require an external dependency.
