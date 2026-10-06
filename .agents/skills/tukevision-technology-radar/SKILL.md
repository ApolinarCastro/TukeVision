---
name: tukevision-technology-radar
description: Evaluate external repositories, standards, papers, books, vendor products, models, and engineering patterns against real TukeVision gaps and TES evidence. Use for radar refreshes, bibliography reviews, source discovery, new technology proposals, licensing checks, or dependency recommendations.
---

# TukeVision Technology Radar

## Source hierarchy

Discovery is not authority.

Use:
`DISCOVERY -> ORIGINAL SOURCE -> VERSION/REF -> LICENSE -> CAPABILITIES -> TUKEVISION MAP -> BENCHMARK -> DECISION`.

Examples:
- discovery corpus/catalogs can suggest candidates;
- upstream repository/docs/standards establish technical facts;
- TukeVision benchmark decides adoption.

## Required source record

For every material source capture:
- canonical upstream;
- forge/source type;
- version/tag/commit/date;
- license/provenance;
- verified capability;
- affected TukeVision problem/capability;
- adoption boundary;
- benchmark required;
- revisit condition;
- final classification.

## Valid classifications

`YA_RESUELTO | ADAPTAR | INTEGRAR | BENCHMARK | WATCH | RESERVE | REJECT`.

Do not create a new component if TES already contains a sufficient solution.

## Materiality

Update TES only if a source changes materially:
- capability;
- maturity;
- license;
- compatibility;
- security;
- cost/performance;
- affected TukeVision gap;
- classification/decision;
- revisit condition.

## External knowledge rule

Books, papers, vendor docs, and community knowledge may produce reusable engineering patterns, but:
- separate principles from vendor-specific claims;
- do not copy restricted code/content;
- validate time-sensitive claims against current primary sources;
- convert durable insights into tests/contracts, not slogans.

## Knowledge-to-skill rule

Create/modify a skill only when the knowledge describes a repeated workflow or decision procedure. Facts belong in TES/reference records; procedures belong in skills.

## Acceptance

A radar task is complete when:
- relevant source is verified;
- duplication check is done;
- license boundary is explicit;
- benchmark/adoption boundary is explicit;
- TES is updated only if material;
- no runtime/dependency change occurs without a separate approved implementation task.
