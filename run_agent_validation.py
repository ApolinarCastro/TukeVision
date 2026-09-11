import time
import psutil
import os
import json
import logging
import pytest
import sys
from datetime import datetime
from src.agent.control import AgentControlConfig, AgentController
from src.agent.monitor import AgentMonitor
from src.agent.reasoning import DeterministicReasoner
from src.agent.audit import AgentAuditLog
from src.agent.attention_orchestrator import AttentionOrchestrator

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("agent_validation")

def measure_resources():
    process = psutil.Process(os.getpid())
    return {
        "rss_mb": process.memory_info().rss / 1024 / 1024,
        "cpu_percent": process.cpu_percent(interval=0.1)
    }

def run_resource_budget_test():
    logger.info("Starting Resource Budget Test (Agent ON vs Agent OFF)...")
    
    # 1. Measure Baseline
    base_resources = measure_resources()
    logger.info(f"BASELINE: RSS={base_resources['rss_mb']:.1f}MB, CPU={base_resources['cpu_percent']}%")
    
    # 2. Run with Agent ON
    orchestrator = AttentionOrchestrator()
    audit = AgentAuditLog("data/val_audit.jsonl")
    reasoner = DeterministicReasoner()
    monitor = AgentMonitor(reasoner, audit)
    
    config_on = AgentControlConfig(enabled=True)
    agent_on = AgentController(monitor, config_on)
    
    t0 = time.time()
    for i in range(100):
        c = orchestrator.process_observation(
            entity_id=f"E{i}", zone_id="Z1", behavior="walking", 
            situation_type="movement", camera_id="cam_01", timestamp=time.time()
        )
        if c.status == "NEW":
            agent_on.investigate(c)
            
    on_resources = measure_resources()
    on_time = time.time() - t0
    logger.info(f"AGENT_ON (100 candidates): Time={on_time:.2f}s, RSS={on_resources['rss_mb']:.1f}MB, CPU={on_resources['cpu_percent']}%")
    
    # 3. Run with Agent OFF
    config_off = AgentControlConfig(enabled=False)
    agent_off = AgentController(monitor, config_off)
    
    t0 = time.time()
    for i in range(100, 200):
        c = orchestrator.process_observation(
            entity_id=f"E{i}", zone_id="Z1", behavior="walking", 
            situation_type="movement", camera_id="cam_01", timestamp=time.time()
        )
        if c.status == "NEW":
            agent_off.investigate(c)
            
    off_resources = measure_resources()
    off_time = time.time() - t0
    logger.info(f"AGENT_OFF (100 candidates): Time={off_time:.2f}s, RSS={off_resources['rss_mb']:.1f}MB, CPU={off_resources['cpu_percent']}%")
    
    return {
        "baseline": base_resources,
        "agent_on": on_resources,
        "agent_off": off_resources,
        "time_overhead_ms_per_candidate": (on_time - off_time) * 10
    }

def main():
    logger.info("=== MACRO-TUKEVISION-V3: PHASE 4 VALIDATION ===")
    
    # 1. Run Regression Tests
    logger.info("Running Unit Test Regression...")
    result = pytest.main(["tests/", "-v", "-k", "agent"])
    if result != 0:
        logger.error("Regression tests failed! Aborting validation.")
        sys.exit(1)
        
    # 2. Run Resource Budget
    budget = run_resource_budget_test()
    
    # 3. Validation Report
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "phase": "F4-AGENT-MONITOR",
        "regression_status": "PASS",
        "resource_budget": budget
    }
    
    os.makedirs("evidence/TV-F4-AGENT-MONITOR-INVESTIGATION-01", exist_ok=True)
    report_path = "evidence/TV-F4-AGENT-MONITOR-INVESTIGATION-01/f4_validation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
        
    logger.info(f"Validation complete. Report written to {report_path}")

if __name__ == "__main__":
    main()
