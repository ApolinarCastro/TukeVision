import os
import logging
from typing import Optional

logger = logging.getLogger("agent_control")

class AgentControlConfig:
    """
    Manages the operational mode and kill switch for the Agent Monitor.
    """
    def __init__(self, enabled: Optional[bool] = None, mode: Optional[str] = None):
        # Allow passing explicitly, otherwise read from ENV
        self._enabled = enabled if enabled is not None else os.environ.get("AGENT_ENABLED", "true").lower() == "true"
        self._mode = mode if mode is not None else os.environ.get("AGENT_MODE", "NORMAL").upper()
        
    @property
    def is_enabled(self) -> bool:
        return self._enabled
        
    @property
    def is_safe_mode(self) -> bool:
        return self._mode == "SAFE"

    def set_enabled(self, enabled: bool):
        logger.info(f"AGENT_ENABLED set to {enabled}")
        self._enabled = enabled
        
    def set_mode(self, mode: str):
        if mode not in ("NORMAL", "SAFE"):
            raise ValueError("Mode must be NORMAL or SAFE")
        logger.info(f"AGENT_MODE set to {mode}")
        self._mode = mode

class AgentController:
    """
    Wraps the AgentMonitor to respect ControlConfig.
    If disabled, returns None for investigation.
    If safe mode, ensures no external calls are made (enforced at the reasoner level or here).
    """
    def __init__(self, monitor, config: AgentControlConfig):
        self.monitor = monitor
        self.config = config
        
    def investigate(self, candidate):
        if not self.config.is_enabled:
            logger.debug("Agent is disabled. Skipping investigation.")
            return None
            
        if self.config.is_safe_mode:
            # Enforce that the reasoner used is local/read-only
            # For Phase 4, our DeterministicReasoner is inherently safe.
            # If we had a VLM reasoner, we would intercept it here or swap it.
            logger.debug("Agent is operating in SAFE MODE.")
            
        return self.monitor.investigate(candidate)
