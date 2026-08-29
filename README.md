# TukeVision

**Local-first Operational Intelligence for existing CCTV infrastructure.**

TukeVision is a vendor-neutral computer vision platform designed to transform existing CCTV video streams into traceable observations, temporal entities, situations, evidence and governed operator workflows — without requiring replacement of the installed camera infrastructure.

> **Español:**  
> TukeVision es una plataforma local y neutral respecto del fabricante que agrega inteligencia operacional a infraestructuras CCTV existentes, transformando video en observaciones, seguimiento temporal, situaciones, evidencia trazable y flujos gobernados para operadores — sin necesidad de reemplazar las cámaras instaladas.

---

## What TukeVision is

TukeVision layers intelligent operational reasoning on top of existing commercial CCTV systems (DVR, NVR, IP cameras). It is designed to work in edge and on-premise environments, keeping video feeds and data strictly local.

- **Non-Invasive Enhancement:** Does not replace cameras, DVRs, or VMS systems; connects to available streams (e.g., via RTSP).
- **Local-First & Edge-Native:** Ingestion, inference, tracking, and evidence packaging run on local infrastructure without mandatory cloud connectivity.
- **Vendor-Neutral:** Agnostic to camera manufacturers and recording hardware.
- **Human-in-the-Loop Governance:** Autonomous monitoring investigates and flags situations, while critical and sensitive responses remain governed and subject to human oversight.

### Conceptual Hierarchy

TukeVision strictly separates perceptual facts from business situations:

$$\text{Detection} \neq \text{Track} \neq \text{Entity} \neq \text{Behavior} \neq \text{Situation}$$

- **Detection:** An instantaneous bounding box observation in a single video frame.
- **Track:** A continuous kinematic trajectory across sequential frames in a specific camera.
- **Entity:** A persistent temporal subject tracked across time, zones, and camera transitions.
- **Behavior:** Temporal patterns, dwell times, directional flow, and interaction indicators.
- **Situation:** A synthesized operational scenario (e.g., checkout congestion, unattended area, safety anomaly) supported by correlated evidence.

---

## Architecture

TukeVision follows a unidirectional pipeline from raw stream ingestion to governed operator action:

```text
CCTV / Video Sources (RTSP / Local Feeds)
        ↓
Universal Ingestion & Stream Supervision (FFmpeg / OpenCV)
        ↓
Perception (YOLO / OpenVINO / Selective Inference)
        ↓
Tracking (ByteTrack / Spatiotemporal Association)
        ↓
Temporal Entity State (Multi-camera / Ground-plane reasoning)
        ↓
Behavior & Temporal Reasoning (Dwell time, zones, flow)
        ↓
Situation Candidates (Correlation & anomaly scoring)
        ↓
Evidence Selection (Frame clips, telemetry, audit hashes)
        ↓
Operational Intelligence Engine
        ↓
Agent Monitor (Autonomous multi-level investigation)
        ↓
Governed Operator Workflow (Human review & authorized actions)
```

---

## Core Principles

- **Local-First / Edge Processing:** Processing happens close to the source to minimize latency and bandwidth.
- **Data Sovereignty:** Video and business metadata remain within the client's network boundary.
- **Vendor Neutrality:** Standardized ingestion interfaces independent of proprietary hardware locks.
- **Evidence-First Reasoning:** Every alert or situation is bound to reproducible timestamps, frame captures, and forensic metadata.
- **Provenance & Confidence:** Explicit tracking of observation states, confidence levels, and model versions.
- **Human Oversight:** High-stakes actions require human verification (*fail-closed* design).
- **Source Isolation & Resource Bounds:** Camera feeds operate in supervised boundaries to prevent system-wide memory or CPU starvation.
- **No Facial Recognition by Default:** No biometric identification or individual facial profiling.
- **Auditability:** Tamper-evident logging for all generated evidence packages and operator decisions.

---

## Current Capabilities

The repository contains concrete, code-implemented modules covering:

- **RTSP & Video Ingestion:** Supervised multi-stream ingestion with reconnection policies and frame buffers (`src/capture/`).
- **Inference Optimization:** CPU-optimized object and person detection using OpenVINO and PyTorch engines (`src/inference/`, `src/detection/`).
- **Temporal Tracking & Entity State:** Trajectory management, ID persistence, and spatiotemporal association (`src/tracking/`, `src/temporal/`).
- **Spatial & Zone Intelligence:** Polygonal ROI monitoring, dwell-time computation, and trajectory analysis (`src/spatial/`, `src/scene/`).
- **Behavior & Situation Reasoning:** Rule-based and heuristic situation candidate generation (`src/behavior/`, `src/correlation/`).
- **Evidence Packaging:** Structured bundles containing video clips, keyframes, telemetry, and SHA-256 manifests (`src/evidence/`).
- **Agent Monitor:** Multi-level investigative monitor with read-only scene queries (`src/agent/`).
- **Governed Operational Actions:** Policy-driven notification and action dispatch with human authorization gates (`src/operator/`, `src/alerts/`).
- **Experience & Learning Store:** Local storage of operational patterns and feedback (`src/learning/`, `src/business/`).
- **Operational UI:** Real-time desktop dashboard built in Tkinter for operators and field engineers (`src/ui/`, `src/visualization/`).
- **Multi-Store Architecture:** Logical support for multi-branch environments (`src/multisite/`).

---

## Operational Intelligence

TukeVision shifts monitoring from passive screen observation to active operational questioning:

1. **What is happening?** — Identifies active events (e.g., dwell in restricted zone, customer queue formation).
2. **Where is it happening?** — Maps detections to specific zones, cameras, and store coordinates.
3. **Which entity is involved?** — Associates observations with persistent temporal entity IDs.
4. **How long has it persisted?** — Measures duration, dwell times, and velocity profiles.
5. **What evidence supports the situation?** — Packages synchronized video clips, bounding boxes, and sensor data.
6. **What is known vs. inferred?** — Distinguishes directly observed optical detections from kinematic estimates.
7. **Does the situation require operator attention?** — Calculates priority scores based on operational rules.
8. **What governed response is allowed?** — Evaluates action policies (notify, log, prompt human review).

---

## Cascade Intelligence

To operate efficiently on edge hardware, TukeVision employs selective computational escalation:

```text
Stream Metadata & Frame Differencing
        ↓ (Motion detected)
Lightweight Person / Object Detector
        ↓ (Object confirmed)
Temporal Tracker & Trajectory Filter
        ↓ (Dwell or zone rule triggered)
Temporal Reasoning & Spatial Analysis
        ↓ (Anomaly threshold reached)
Local Semantic & Situational Reasoning
        ↓ (Ambiguity or high-priority risk)
Agent Monitor Deep Investigation
```

*Note: Escalation levels are triggered on demand based on scene activity rather than running continuously on all channels simultaneously.*

---

## Safety and Governance

TukeVision enforces a strict autonomy policy for operational security:

| Level | Name | Description |
| :--- | :--- | :--- |
| **`AUTONOMY_0`** | **Observe** | Passive monitoring, stream ingestion, telemetry collection. |
| **`AUTONOMY_1`** | **Investigate** | Automated scene inspection, correlation, and evidence extraction. |
| **`AUTONOMY_2`** | **Limited Governed Action** | Low-risk automated logging, local metric updates, and routing alerts. |
| **`AUTONOMY_3`** | **Sensitive Action (Human Approval)** | High-stakes dispatch, external notifications, and operational escalation. **Always requires explicit human confirmation.** |

---

## Privacy

- **No Facial Recognition:** TukeVision does not extract facial embeddings or perform individual identity recognition in its core architecture.
- **Non-Biometric Tracking:** People are tracked as anonymous temporal bounding boxes and spatial vectors within the store.
- **Local Data Retention:** Video and audit trails reside on-premises under customer control.
- **Privacy-Aware Evidence:** Evidence clips are strictly limited to relevant event time windows.

---

## Technology Stack

- **Core Language:** Python 3.12 (64-bit)
- **Computer Vision & Video:** OpenCV, FFmpeg, Ultralytics YOLO
- **Inference Acceleration:** Intel OpenVINO Toolkit, ONNX Runtime, PyTorch
- **Data & Persistence:** SQLite, JSONL, Local File Bundles
- **Desktop Interface:** Python Tkinter (Native GUI)
- **Scripting & Automation:** PowerShell, Bash

---

## Project Status

TukeVision is under active engineering development.

The repository contains an operational computer-vision and CCTV intelligence stack that has progressed well beyond the original single-video prototype. Multiple operational capabilities (multi-camera RTSP ingestion, OpenVINO inference, temporal entity tracking, situation synthesis, and governed evidence generation) are fully implemented and verified via automated test suites.

Advanced multi-stream HD visualization and specific field runtime configurations remain under structured physical soak validation. Repository documentation strictly distinguishes implemented code capabilities from physically certified operational deployments.

---

## Development Philosophy

TukeVision adheres to an evidence-driven, test-guided development methodology:

$$\text{Observe} \longrightarrow \text{Trace} \longrightarrow \text{Identify Root Cause} \longrightarrow \text{Correct} \longrightarrow \text{Test} \longrightarrow \text{Validate Physically} \longrightarrow \text{Stabilize} \longrightarrow \text{Certify} \longrightarrow \text{Stop}$$

- **Architecture before integration:** Clear contracts and data boundaries precede external integrations.
- **Evidence before claims:** No capability is considered verified merely because a configuration or DTO declares it.
- **Clean-room adaptation:** External patterns are studied methodically; third-party code is never integrated without explicit architectural justification and license compliance.

---

## Repository Structure

```text
├── src/            # Core platform implementation
│   ├── agent/      # Autonomous Agent Monitor & tool interfaces
│   ├── capture/    # RTSP, FFmpeg, and multi-camera stream ingestion
│   ├── detection/  # Object and person detection modules
│   ├── inference/  # OpenVINO / PyTorch inference execution engines
│   ├── tracking/   # Multi-object tracking (ByteTrack & spatial filters)
│   ├── temporal/   # Temporal entity states & trajectory persistence
│   ├── behavior/   # Behavior and dwell-time reasoning
│   ├── correlation/# Situation candidate generation & correlation
│   ├── evidence/   # Evidence packaging, hashing & verification
│   ├── operator/   # Governed actions & human review workflows
│   ├── ui/         # Tkinter desktop operator interface
│   └── ...
├── config/         # Runtime configurations, zone definitions & schemas
├── docs/           # Architecture design records, runbooks & technical specs
├── evidence/       # Validation runs, forensic traces & certification artifacts
├── models/         # Model weights directory (OpenVINO IR / ONNX / PT)
├── scripts/        # Engineering, benchmarking & operational utility scripts
└── tests/          # Automated unit, regression & integration test suite
```

---

## Disclaimer

TukeVision is an actively developed operational-intelligence platform. Capabilities, integrations, and certification states evolve through structured phases. Refer to repository validation artifacts and tagged release baselines for the exact verified state of any given build.
