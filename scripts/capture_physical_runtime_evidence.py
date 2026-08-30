"""Physical Runtime Telemetry & Acceptance Evidence Collector for TukeVision.

EXECUTION_ID: TV-F12-MEGALOOP-RUNTIME-TRUTH-CLOSURE-05
Attached directly to the MAIN MulticameraRuntime and TkApp in the SAME process.
"""

from __future__ import annotations

import json
import os
import sys
import time
import tkinter as tk
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from scripts.run_multicamera import MulticameraRuntime
from src.observability.runtime_evidence_collector import (
    RuntimeContext,
    RuntimeEvidenceCollector,
)
from src.ui.tk_view import TkApp


def main() -> int:
    print("[*] Starting TukeVision live runtime for physical recertification...")
    config_path = BASE / "config" / "multistore.active.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Resolve credentials from env if available
    creds_json = os.environ.get("ENV_DVR_PRINCIPAL_CREDS", "{}")
    try:
        creds = json.loads(creds_json)
        user = creds.get("username", "")
        password = creds.get("password", "")
    except Exception:
        user = ""
        password = ""

    run_id = "TV-F12-MEGALOOP-RUNTIME-TRUTH-CLOSURE-05"
    start_time = time.time()

    # 1. Initialize the real MulticameraRuntime
    runtime = MulticameraRuntime(config, password=password, user=user, run_id=run_id)
    runtime.start()
    if hasattr(runtime, "_telemetry") and runtime._telemetry is not None:
        runtime._telemetry.start()

    # 2. Initialize the real TkApp window
    root = tk.Tk()
    app = TkApp(root, runtime)
    root.update_idletasks()
    root.update()

    # 3. Construct the RuntimeContext with shared live references
    context = RuntimeContext(
        source_manager=runtime._manager,
        tk_app=app,
        health_sampler=runtime._health,
        true_liveness=runtime._true_liveness,
        multicamera_runtime=runtime,
        run_id=run_id,
        start_time=start_time,
        pid=os.getpid(),
    )

    # 4. Attach the Evidence Collector
    collector = RuntimeEvidenceCollector(context)

    try:
        # Collect runtime identity (same_process=YES, live source_manager)
        collector.collect_runtime_identity()

        # Collect physical camera health & liveness ($T_0$ vs $T_1$)
        collector.collect_physical_camera_health_and_liveness()

        # Collect Focus HD on real cameras
        collector.collect_focus_hd(["cam_01", "cam_06", "cam_09"])

        # Measure Grid6 geometry and UX acceptance
        collector.collect_grid6_and_ux_acceptance()

        # Capture real application window screenshots
        collector.capture_real_screenshots()

        # Execute soak sampling (1800s in certification mode or TUKEVISION_SOAK_SECONDS env override)
        soak_target = int(os.environ.get("TUKEVISION_SOAK_SECONDS", 1800))
        collector.execute_soak_sampling(target_duration_seconds=soak_target)

        # Execute complete regression test suite and parse output
        collector.run_regression_and_parse()

        # Finalize truth gates and TES reconciliation
        collector.write_truth_gates_and_tes()

        print(f"[OK] Physical runtime evidence collection complete. Artifacts in: {collector.evidence_dir}")
        return 0

    except Exception as e:
        print(f"[!] Error during evidence collection: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        try:
            runtime.stop()
            runtime.close()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
