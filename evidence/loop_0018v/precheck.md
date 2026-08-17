# LOOP-0018V — Phase 0 precheck

- BASE: `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision`
- Branch: `product/loop-0018r-temporal-tracking`
- HEAD: `2030612`
- Worktree before: pre-existing untracked `evidence/loop_0018m_r1/`,
  `evidence/loop_0018s/`, and `src/capture/live_sources.BASE_preE01.bak.py`;
  preserved and excluded from LOOP-0018V ownership.
- BASE runtime: `.venv`, Python 3.12.10 (`pyvenv.cfg`).
- Root structure: `TukeVision + TES + archive`.
- Former portable/testinstall roots: absent.
- Runtime portable references in `src`, `config`, scripts, launcher: 0.
- Reused components present: `SourceManager`, `ActivityLayer`,
  `SelectiveInferencePipeline`, `EventDetector`, `LocalTracker`,
  `src/app/advance_chain.py`.
- Active config: `config/default.json`.
- Baseline: `Ran 370 tests in 29.717s — OK (skipped=4)`.
- Compileall: PASS (`python -m compileall -q src tests`).
- Secret contract: `Ran 22 tests — OK` (`test_secret_leak` plus repository
  no-secret scan).

No code was changed before completion of this precheck.
