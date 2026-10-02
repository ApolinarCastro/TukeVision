# NVIDIA AI for Media / Maxine — TukeVision source record

**VERIFIED_AT:** 2026-10-02  
**SCOPE:** 3D Body Pose, Eye Contact, Relighting, Video Super Resolution (VSR)  
**PRODUCT_CHANGE:** NONE

## 3D Body Pose

Official page: https://build.nvidia.com/nvidia/body-pose  
Docs: https://docs.nvidia.com/nim/maxine/body-pose/latest/

Verified:
- accepts video plus tracked bounding boxes;
- returns tracker-aligned per-frame pose data;
- Nova-77 output includes 2D keypoints, confidence, 3D joints, rest pose, joint rotations and root pose;
- constant frame rate required for frame-to-tracker alignment;
- local container host is Linux amd64 with supported NVIDIA GPU;
- 24 GB is NVIDIA's validated floor, not a measured minimum;
- pose inference cost scales with bodies per frame;
- trial API is cloud-backed and therefore not authorized for customer CCTV.

TukeVision classification: ACTIVE_EVALUATION / HIGH.

## Eye Contact

Official page: https://build.nvidia.com/nvidia/eyecontact  
Docs: https://docs.nvidia.com/nim/maxine/eye-contact/1.5.0/

Verified purpose: synthetically redirects gaze to simulate eye contact. It is not a CCTV gaze detector. The pipeline uses face tracking/head pose internally and returns modified video.

TukeVision classification: REJECT_CORE / RESERVE_REFERENCE.

## Relighting

Official page: https://build.nvidia.com/nvidia/relighting  
Docs: https://docs.nvidia.com/nim/maxine/relighting/latest/

Verified purpose: foreground/background segmentation plus synthetic HDRI relighting/compositing.

TukeVision classification: REJECT_CORE / RESERVE_DERIVED_VIEW.

## Video Super Resolution

Official page: https://build.nvidia.com/nvidia/vsr  
Docs: https://docs.nvidia.com/nim/maxine/vsr/latest/

Verified:
- current documented NIM release 1.0.10;
- compressed-video workflows and ST 2110 workflows;
- Ada-or-later GPU, driver 590.33+, CUDA 13.1+ shared requirements;
- compressed workflow supports H.264/H.265/AV1 and target scaling up to 4x per dimension.

TukeVision classification: BENCHMARK / DERIVED_VIEW_ONLY.

## Permanent evidence boundary

```text
ORIGINAL_EVIDENCE
!=
DERIVED_AI_VIEW
```

VSR/Relighting/Eye Contact outputs may not replace canonical source evidence. Any future derived view must be visibly labeled, provenance-linked and reversible to the original source.

## Adoption boundary

None of these sources authorizes implementation while Gate 0C physical validation is pending. 3D Body Pose is the only item from this set that directly maps to future behavior/loss-prevention analytics.
