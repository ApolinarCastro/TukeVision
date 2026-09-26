# Jev / TypeSafe AI — System One Models — Source Record

**VERIFIED_AT:** 2026-09-25  
**CLASSIFICATION:** WATCH / EXPERIMENTAL  
**TUKVISION_ROLE:** Experimental Event Decision Engine  
**PRODUCTION_READY:** FALSE  
**CORE_DEPENDENCY:** FALSE  
**TESTED_WITH_TUKEVISION:** FALSE

## Sources verified

- TypeSafe AI official launch: https://typesafe.ai/blog/introducing-system-one-models-and-jev
- TypeSafe API OpenAPI/Swagger: https://api.typesafe.ai/docs
- Python SDK: https://github.com/typesafe-ai/typesafe-sdk-python
- JavaScript/TypeScript SDK: https://github.com/typesafe-ai/typesafe-sdk-js
- Vercel AI Gateway model page: https://vercel.com/ai-gateway/models/jev
- Vercel gateway HTTP/client support: https://vercel.com/changelog/ai-gateway-now-supports-typesafe-clients-and-http-api-for-jev
- Cloudflare Workers AI model page: https://developers.cloudflare.com/ai/models/typesafe/jev/

## Verified capability

Jev is TypeSafe AI's first public System One model. Its public contract is structured state plus typed questions, returning typed decisions with probabilities/confidence rather than generated prose. Public interfaces expose Choice, Score and Noul/boolean-style decisions. The official API documents `POST /v1/systemone` and `GET /v1/models`.

Official Python and JavaScript/TypeScript SDKs exist. Vercel exposes Jev through AI Gateway and Cloudflare exposes a third-party Jev route through Workers AI. Cloudflare currently marks its Jev route as Zero Data Retention.

Current public descriptions are text/structured-state oriented. Do not treat Jev as a vision, video, audio, ReID, OCR or temporal-analysis model.

## Provider claims that are NOT TukeVision evidence

TypeSafe reports large speed/cost advantages on its own System One workflow evaluations. These remain provider claims until a TukeVision benchmark reproduces them. Calibration is a population/evaluation property and cannot be assumed to make an individual decision correct.

## TukeVision boundary

```text
Event facts / deterministic correlation
→ Jev proposal
→ Policy Engine
→ allowed next step
→ evidence / operator
```

Never `Jev -> direct action`.

Preserve:
- FACT != INFERENCE
- INFERENCE != EVIDENCE
- NO_EVIDENCE != NEGATIVE_EVIDENCE
- UNKNOWN is valid
- deterministic safety rules override model scores

## Privacy

First lab, if authorized, must send metadata only. No customer video, faces, biometric identifiers or live CCTV to TypeSafe/Vercel/Cloudflare without an explicit privacy/security decision. Gateway privacy properties must be verified for the exact provider/path used.

## License / service boundary

Jev is a hosted model/service, not an open-weight dependency in TukeVision. SDK licenses and service terms must be checked independently before any lab dependency is added. This source record authorizes research only, not dependency installation or production use.
