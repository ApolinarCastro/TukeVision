---
name: tukevision-project-execution-gate
description: Enforce TukeVision project-state recovery, anti-hallucination gates, finite execution, acceptance evidence, and no-duplicate-design rules. Use before any material analysis, architecture, implementation, debugging, test, recommendation, or continuation of TukeVision work.
---

# TukeVision Project Execution Gate

## Objective

Prevent context drift, speculative architecture, false progress, duplicated components, and infinite development loops.

## Required preflight

Before material work:

1. Identify the exact task and subsystem.
2. Read the current repository truth:
   - README/current state if present;
   - current branch and HEAD;
   - current task/blocker;
   - `TES/DECISION_LOG.md`;
   - `TES/EXPERIENCE_STORE.md`;
   - `TES/KNOWLEDGE_SOURCE_INDEX.md`;
   - `TES/TECHNOLOGY_RADAR.md`;
   - relevant capability matrix, failures, risks, acceptance, and evidence.
3. Determine the first blocking checkpoint.
4. Search existing capabilities before proposing a new module.
5. Search TES before proposing a new technology or pattern.

## State discipline

Use only explicit task states:
`NOT_TESTED | READY | IN_PROGRESS | FAIL | BLOCKED | PASS | CLOSED`.

Never:
- jump from `NOT_TESTED` to `PASS`;
- mark a proposal as implemented;
- mark tests as passed without evidence;
- convert a documentation assertion into runtime truth.

## Execution loop

`PLAN -> MINIMUM TEST -> IMPLEMENT/ANALYZE -> REVIEW -> VERIFY -> RECORD -> STOP`

Every loop must have:
- Task ID;
- objective;
- dependencies;
- first blocker/failure;
- acceptance criterion;
- minimum decisive test;
- evidence required;
- result;
- exact next action.

## Resource gate

Before adding a framework, database, queue, agent, model, protocol, service, or dependency, answer:
- What measured gap does it solve?
- What existing component already addresses this?
- What is the smallest benchmark?
- What resource cost does it add?
- What regression risk does it add?
- What rollback exists?

If no real gap exists, classify `YA_RESUELTO` or `REJECT`.

## Acceptance

A task is `PASS` only when the stated acceptance criterion is supported by repository/runtime evidence appropriate to the claim.
