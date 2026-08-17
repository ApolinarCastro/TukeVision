# LOOP-0018Z addendum — operator launcher and four-camera view

LAUNCHER_PATH: `start_tukevision.ps1` exists; no `.bat` launcher was added.
BASE_RUNTIME_USED: YES (existing PowerShell launcher resolves BASE `.venv`).
PORTABLE_RUNTIME_USED: NO.
FOUR_CAMERA_VIEW: BLOCKED_ARCHITECTURAL_SCOPE.
CAMERAS_OPEN_VIA_SOURCEMANAGER: PARTIAL — the certified validation harness uses SourceManager.
DIRECT_UI_VIDEOCAPTURE: NO — no direct four-camera UI capture was introduced.
CREDENTIAL_MECHANISM: existing local `getpass` in the validation harness.
CREDENTIAL_PERSISTENCE: 0.
SECRET_LEAK: 0 observed.
CLEAN_SHUTDOWN: PASS for the stopped validation process; no code/config change.
ORPHAN_PROCESS: not observed for the launched validation process.
FOCUSED_TESTS: 140 PASS before addendum.
FULL_REGRESSION: 411 PASS / 4 optional skips before addendum.

## Reuse and scope decision

Existing launch surface: `start_tukevision.ps1` → `scripts/run_interface.py` →
`UiController`/`TkApp`. The current UI accepts one source and one operational
pipeline. No existing four-camera composition view was found. A 2×2 view would
require new multi-source UI orchestration and state/rendering changes, exceeding
the addendum's “minimal adapter” boundary. Per instruction, validation STOPPED
at this divergence; no `.bat`, UI code, thresholds, or configuration was changed.
