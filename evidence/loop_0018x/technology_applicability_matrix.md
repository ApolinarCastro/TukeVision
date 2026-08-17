# Technology applicability matrix

Evidence consumed: TES Technology Ingestion Playbook, Technology Radar Master, Technology Extension Map, External Experience Catalog and Technology/Reference Registry. This is controlled reuse of existing research, not a new general search.

| Candidate | Need covered | Fit now | Dependencies/data | Governance | Decision |
|---|---|---|---|---|---|
| Existing Python contracts/rules | durations, counts, sequences, evidence | Direct P0 fit | none | compliant | USE_NOW / INTERNAL_REUSE |
| RetailS patterns | pose, zones, temporal sequence | useful later | pose models and validation data | requires privacy review | DEFER |
| 1amitos1 SlowFast/3D-CNN | action classification | backend reference only | model, runtime, goldens | intent/guilt labeling risk | DEFER |
| CNN+GRU research pattern | temporal activity | reference only | training and goldens | requires explicit taxonomy | DEFER |
| Shopformer | advanced action classification | premature | model/data/compute | requires controlled POC | DEFER |
| PyResearch shoplifting detector | binary shoplifting label | incompatible with objective | model/data/dependency | accusatory label | REJECT |
| Veesion/TheftGuard product patterns | human review, clips, zones | pattern value only | no removable adapter available | label taxonomy needs review | PATTERN_REUSE_ONLY |
| OpenVINO | inference acceleration | no measured P0 gap | new runtime/backend | compliant if later isolated | DEFER |
| ReID/OSNet/OpenVINO MCMOT | identity-like correlation | not needed | models/runtime/data | prohibited | GOVERNANCE_BLOCKED |
| Graph tooling/NetworkX | trajectory graphs | existing structures suffice | unnecessary dependency | compliant but no value | NOT_REQUIRED_YET |

`EXTERNAL_TECHNOLOGY_INGESTED=NO`: no external candidate passes the playbook gate without new models, datasets, dependencies, or a governance decision. Forcing one would add risk without improving the P0 deterministic behavior/risk pipeline.
