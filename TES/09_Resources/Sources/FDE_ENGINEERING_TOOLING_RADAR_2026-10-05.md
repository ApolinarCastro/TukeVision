# FDE Engineering Tooling — Source Record 2026-10-05

**PROJECT:** TukeVision  
**EXECUTION_ID:** `TV-RADAR-FDE-ENGINEERING-2026-10-05`  
**MODE:** `RADAR_ONLY`  
**INSTALLATION_PERFORMED:** `NO`  
**PRODUCT_INTEGRATION_PERFORMED:** `NO`  
**RUNTIME_CHANGED:** `NO`

## Persistent state recovered

- Canonical branch: `feature/product-evolution-v1`.
- Canonical head at evaluation start: `07a8fc8d9538ce00af6cf2a01753a82dfc9d62e6`.
- Remote runtime baseline: `0d3640571dfcd737958903ae3fb52b8fe425cee4`.
- Current product checkpoint: `TV-GATE0C-PHYSICAL-CLOSE-004`.
- Current blocker: `MISSING_OPERATOR_UI_EVIDENCE_AND_COMPLETE_600S_ACCEPTANCE`.

No candidate in this record resolves that blocker.

## Governance applied

- `07_PROJECT_EXECUTION_OS_TASKVIEW_ECC`.
- `06_ANTI_HALLUCINATION_AND_RESOURCE_GATE`.
- Persistent execution contract associated with `08_DEVIN_EXECUTION_ARCHITECTURE_STANDARD`.

The exact named `08_DEVIN_EXECUTION_ARCHITECTURE_STANDARD` artifact was not found in the TukeVision repository. It was not invented as a repo-local file. The available persistent execution standard was applied: scope/dependency/knowledge recovery before planning, explicit execution contract and rollback, bounded implementation, validation/review, knowledge capture, and strict evidence classification.

## 1. closedloop-ai/claude-plugins

- **REF:** `e22099008fe79b289c92a9e2598783cd7cdcfb65`.
- **LICENSE:** Apache-2.0.
- **OBSERVED CAPABILITIES:** plan agents and implementation-plan artifacts; code-review workflows; plan/code/PRD/feature judges with deterministic aggregation; persistent self-learning/pattern store with validation/deduplication/confidence/staleness.
- **GAP FIT:** execution quality, not product runtime.
- **CLASSIFICATION:** `RELEVANTE`.
- **DECISION:** adapt selected patterns only; no installation.
- **BOUNDARY:** LLM-as-judge = advisory evidence, never certification authority.

## 2. ix-infrastructure/Ix

- **REF:** `677e0f440055b03c00e47c19a52f6d93652edd4c`.
- **LICENSE:** Apache-2.0.
- **OBSERVED CAPABILITIES:** tree-sitter mapping into persistent local graph; symbols/calls/imports/relationships; explain/trace/impact; CLI/MCP access.
- **OBSERVED DEPENDENCY FOOTPRINT:** Node tooling plus Docker/ArangoDB/memory backend in current upstream architecture.
- **GAP FIT:** yes, candidate real engineering gap. No persistent repository structural/impact graph is evidenced in TukeVision.
- **CLASSIFICATION:** `EVALUAR`.
- **DECISION:** only `RI-IX-001` isolated benchmark; no installation now.
- **VENDOR CLAIM BOUNDARY:** upstream token-reduction figures are internal vendor measurements, not TukeVision evidence.

## 3. HKUDS/OpenOPC

- **REF:** `b14e85d8fff8d174a5e8d54c267e50ecae23ceb4`.
- **LICENSE:** MIT.
- **OBSERVED CAPABILITIES:** dependency DAGs, task/work-item state, owners, review/rework/integration, human escalation, learned employee/playbook context, external execution agents.
- **GAP FIT:** no current gap proven. Significant overlap with Project Execution OS and TaskView candidate control-plane role.
- **CLASSIFICATION:** `RADAR`.
- **DECISION:** retain patterns only; no installation/integration.
- **REOPEN CONDITION:** reproducible failure of existing task/dependency/handoff/review governance.

## 4. anomalyco/opencode

- **REF:** `907b3bc518fa48e90e8ec24dd327d13eee71c36c`.
- **LICENSE:** MIT.
- **OBSERVED CAPABILITIES:** read-only plan agent; build agent with execution access; general subagent; configurable permissions/plugins.
- **GAP FIT:** executor/integrator role compatible with current engineering process.
- **CLASSIFICATION:** `RELEVANTE`.
- **DECISION:** executor only under 06/07/08; no architecture replacement; no automatic integration.
- **BOUNDARY:** OpenCode cannot self-certify its own implementation.

## Name disambiguation

`OpenOPC` in this evaluation is `HKUDS/OpenOPC`, not classic OPC industrial communication libraries.  
`OpenCode` is `anomalyco/opencode`, not archived `opencode-ai/opencode`.

## Final classification

| Source | Classification | Integrate now |
|---|---|---|
| closedloop-ai/claude-plugins | RELEVANTE | NO |
| ix-infrastructure/Ix | EVALUAR | NO |
| HKUDS/OpenOPC | RADAR | NO |
| anomalyco/opencode | RELEVANTE | NO |

No item is `DESCARTAR`: each contains at least a reusable pattern or future evaluation value. This does not authorize adoption.
