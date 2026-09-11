import psutil
import os
import logging

logger = logging.getLogger("agent_budget")

class ReasoningBudget:
    """
    Monitors system resources and defines the acceptable reasoning escalation tier.
    States: NORMAL, CONSTRAINED, CRITICAL
    """
    def __init__(self, critical_cpu: float = 95.0, constrained_cpu: float = 80.0, force_state: str = None):
        self.critical_cpu = critical_cpu
        self.constrained_cpu = constrained_cpu
        self.force_state = force_state
        self._pid = os.getpid()

    def evaluate_state(self, queue_depth: int = 0) -> str:
        if self.force_state is not None:
            return self.force_state
        # Check system CPU rather than just process to protect perception
        cpu = psutil.cpu_percent(interval=None) 
        
        if cpu >= self.critical_cpu or queue_depth > 50:
            return "CRITICAL"
        elif cpu >= self.constrained_cpu or queue_depth > 10:
            return "CONSTRAINED"
        
        return "NORMAL"
