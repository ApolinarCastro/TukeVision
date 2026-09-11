import os
import sys
from pathlib import Path
import json
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_strict_runtime_truth import CertificationEvaluator

if __name__ == "__main__":
    base_ev = Path("evidence").resolve()
    print("Waiting for physical_runtime_report.json...")
    
    for _ in range(50):
        try:
            candidate_dirs = [d for d in base_ev.glob("RUN-*") if (d / "live_status.json").exists() and (d / "physical_runtime_report.json").exists()]
            if candidate_dirs:
                candidate_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
                run_dir = candidate_dirs[0]
                check = CertificationEvaluator.evaluate_certification_integrity(run_dir)
                
                print(f"Certification Evaluation for {run_dir.name}:")
                print(json.dumps(check, indent=2))
                
                report = f"# F12 FINAL OBSERVABILITY CERTIFICATION\n\n"
                report += f"**Verdict:** {check.get('recommended_verdict', 'UNKNOWN')}\n"
                report += f"**Reason:** {check.get('reason', '')}\n\n"
                report += f"## Evaluation Details\n```json\n{json.dumps(check, indent=2)}\n```\n"
                
                Path("F12_FINAL_OBSERVABILITY_CERTIFICATION.md").write_text(report, encoding="utf-8")
                print("Generated F12_FINAL_OBSERVABILITY_CERTIFICATION.md")
                sys.exit(0)
        except Exception as e:
            print(f"Error during certification check: {e}")
        time.sleep(1)
    
    print("TIMEOUT waiting for report")
    sys.exit(1)
