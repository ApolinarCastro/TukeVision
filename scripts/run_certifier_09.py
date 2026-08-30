import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.observability.runtime_evidence_collector import RuntimeEvidenceCollector

if __name__ == "__main__":
    collector = RuntimeEvidenceCollector()
    result = collector.collect_final_passive_observer_09()
    print("FINISHED RUN 09. Status:", result)
