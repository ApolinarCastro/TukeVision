---
name: tukevision-stream-onboarding
description: Govern safe, bounded, evidence-driven onboarding of RTSP/ONVIF/LAN/DVR sources in TukeVision. Use for camera discovery, device capability inventory, RTSP validation, ONVIF probing, credential handling, source health, TLS negotiation, network scope, or onboarding security.
---

# TukeVision Stream Onboarding

## Objective

Discover and onboard authorized video sources without uncontrolled scanning, false device identity, unsafe credential behavior, or hidden architecture changes.

## Safe discovery pattern

`EXPLICIT AUTHORIZED TARGETS -> BOUNDED DISCOVERY -> BOUNDED RTSP/ONVIF PROBES -> EVIDENCE CORRELATION -> CAPABILITY INVENTORY -> ONBOARDING DECISION`.

Rules:
- never expand outside the explicit target set;
- port presence alone does not prove device/vendor identity;
- insufficient evidence yields `UNKNOWN`;
- preserve positive and negative evidence;
- produce structured/versioned discovery output.

## Allowed normal behavior

Prefer low-volume, bounded operations such as:
- RTSP `OPTIONS/DESCRIBE` validation;
- bounded unauthenticated ONVIF identity/services/capability reads;
- capability negotiation;
- source health/freshness checks;
- firmware/device metadata inventory when authorized.

## Prohibited normal behavior

Do not make these part of standard onboarding:
- credential guessing/brute force;
- high-rate/Masscan-style sweeps;
- broad vulnerability scanning;
- aggressive full-port modes;
- sensitive image/media capture without need and authorization.

## Security assumptions

Treat discovery, ONVIF responses, callback URIs, scopes, device metadata, and authentication material as hostile/untrusted input.

Require:
- bounded parsing;
- URI/callback sanitization;
- replay/freshness controls where applicable;
- least-privilege network segmentation;
- credential secrecy;
- explicit TLS capability detection.

## RTSP liveness

Do not equate open socket with healthy live stream. Require advancing capture/presentation sequence and bounded frame age.

Recovery must avoid restart storms and require first-frame confirmation.

## Acceptance

Onboarding passes only when:
- target containment = PASS;
- identity/capability evidence is recorded;
- stream liveness is demonstrated where required;
- no out-of-scope probe occurred;
- security-sensitive state is auditable.
