# Radar Refresh — 2026-09-23

## Material change: Qwen-MM-Plugins endpoint credential boundary

- **SOURCE_VERIFIED:** YES — `QwenLM/Qwen-MM-Plugins` official upstream.
- **VERSION_OR_REF_VERIFIED:** `cc6a356e2f02e5637e2b13e383b797cc87d53cae` (2026-09-23), included in current `main` via merge `07736672525443c7f8a3f6405eed37d2236f023f`.
- **LICENSE_VERIFIED:** Apache-2.0.
- **CAPABILITIES_EXTRACTED:** the API layer now treats `DASHSCOPE_BASE_URL + DASHSCOPE_API_KEY` as a generic OpenAI-compatible endpoint pair and scopes that key to the configured URL origin; tool-call `base_url` values targeting another unlisted host receive `EMPTY` instead of the configured credential.
- **TUKEVISION_MAPPING:** future local/selective VLM or multimodal adapters (P0-65/P0-66) and any provider-neutral OpenAI-compatible inference boundary.
- **ADOPTION_BOUNDARY:** pattern only. Do not add Qwen-MM-Plugins as a runtime dependency and do not send customer CCTV to external services. LOCAL_FIRST remains mandatory.
- **REVISIT_CONDITION:** when TukeVision introduces a configurable OpenAI-compatible local/VLM endpoint or any credential-bearing multimodal adapter.
- **EXPERIENCE_RECORD:** `EXP-QWEN-ENDPOINT-CREDENTIAL-001` below.

### Classification

`ADAPTAR | BENCHMARK`

### Materiality

This is security-relevant rather than a feature-only installer change: it makes explicit that endpoint credentials must be bound to an approved origin and must not follow an arbitrary per-call endpoint override. This directly strengthens provider-neutral adapter design without changing the current product architecture.

### TukeVision rule to preserve

```text
CONFIGURED_CREDENTIAL != PORTABLE_CREDENTIAL
credential -> approved origin only
unlisted endpoint override -> no inherited secret
```

### Risk

Without origin binding, a future configurable multimodal/VLM tool could leak a credential when a request overrides `base_url` toward an untrusted or unintended host.

### Minimum benchmark

For any future credential-bearing OpenAI-compatible adapter:
1. configured approved origin receives its configured credential;
2. same-origin path changes preserve expected auth;
3. different/unlisted origin receives no inherited credential;
4. redirects do not silently broaden credential scope;
5. logs/evidence never expose the secret;
6. local-only endpoint remains functional without cloud dependency.

### Next gate

Apply this as a security acceptance criterion when P0-65/P0-66 introduces an actual configurable local VLM/multimodal endpoint. No runtime change is authorized by this radar refresh.

## Experience record

### EXP-QWEN-ENDPOINT-CREDENTIAL-001
- **PROBLEM:** configurable inference endpoints can accidentally carry provider credentials to an overridden/untrusted host.
- **PATTERN:** bind credentials to an explicitly approved endpoint origin; deny credential propagation to unlisted origins.
- **UPSTREAM:** `QwenLM/Qwen-MM-Plugins` ref `cc6a356e2f02e5637e2b13e383b797cc87d53cae`.
- **LICENSE:** Apache-2.0.
- **DECISION:** `ADAPTAR | BENCHMARK` pattern-only.
- **BOUNDARY:** no external CCTV upload; no direct runtime dependency; LOCAL_FIRST and Evidence First remain unchanged.
