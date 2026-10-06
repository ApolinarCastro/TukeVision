---
name: tukevision-agent-governance
description: Govern TukeVision Agent Monitor reasoning, autonomy, tools, actions, escalation, safe mode, probabilistic routing, and model use. Use whenever agent reasoning or a model can influence investigation, prioritization, operational decisions, tools, PTZ, alerts, preservation, or external actions.
---

# TukeVision Agent Governance

## Architectural rule

`DETERMINISTIC CORRELATION -> OPTIONAL MODEL/ROUTER -> POLICY ENGINE -> EXECUTION -> EVIDENCE/VERIFICATION`.

Never:
`MODEL -> DIRECT OPERATIONAL ACTION`.

## Autonomy boundary

Preserve low-risk modes first:
- `AUTONOMY_0`: observe;
- `AUTONOMY_1`: investigate/read-only.

Higher-impact actions require explicit policy, evidence, authorization, and verification.

## Tool policy

Default deny.

Grant only the minimum tools required for the task. Separate:
- read-only investigation tools;
- evidence-preservation tools;
- reversible operator assistance;
- irreversible/external actions.

Tool availability is not permission.

## Epistemic output

Agent results must separate:
- FACTS;
- INFERENCES;
- UNKNOWNS;
- source/evidence references;
- confidence where meaningful.

Never fabricate certainty to fill missing data.

## Kill switch and safe mode

Agent failure must not blind the CCTV system.

Safe mode must be able to:
- stop autonomous/model-driven actions;
- keep capture, health, detection/tracking, and evidence working;
- fall back to observation/read-only behavior;
- alert/log the operator.

## Routing/model layer

A System-One/Jev-like layer may classify, prioritize, score, route, or gate structured events only after deterministic constraints.

It must not replace:
- vision;
- tracking;
- evidence;
- hard safety/business rules;
- legal constraints;
- human confirmation where required.

Promotion path:
`WATCH -> LAB -> BENCHMARK -> CANDIDATE -> PRODUCTION`.

## Acceptance

Unsafe operational action rate must remain zero for any candidate promotion involving autonomous decisions.
