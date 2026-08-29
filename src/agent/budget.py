import psutil
import os
import logging

logger = logging.getLogger("agent_budget")

class ReasoningBudget:
    """
    Monitors system resources and defines the acceptable reasoning escalation tier.
    States: NORMAL, CONSTRAINED, CRITICAL
    """
    def __init__(self, critical_cpu: float = 85.0, constrained_cpu: float = 60.0):
        self.critical_cpu = critical_cpu
        self.constrained_cpu = constrained_cpu
        self._pid = os.getpid()

    def evaluate_state(self, queue_depth: int = 0) -> str:
        # Check system CPU rather than just process to protect perception
        cpu = psutil.cpu_percent(interval=None) 
        
        # We can also add RAM checks, but CPU is usually the bottleneck for local inference
        
        if cpu >= self.critical_cpu or queue_depth > 50:
            return "CRITICAL"
        elif cpu >= self.constrained_cpu or queue_depth > 10:
            return "CONSTRAINED"
        
        return "NORMAL"
