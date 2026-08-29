import time
import logging
from typing import List, Optional, Dict
from src.agent.actions.contract import ProposedAction

logger = logging.getLogger("governed_action_queue")

class GovernedActionQueue:
    """
    Bounded, prioritized action queue with deduplication, expiration, and cancellation.
    """
    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self._queue: List[ProposedAction] = []
        self._actions_by_id: Dict[str, ProposedAction] = {}
        self._dedup_keys: set = set()

    def push(self, action: ProposedAction) -> bool:
        if len(self._queue) >= self.max_size:
            logger.warning("GovernedActionQueue is full. Dropping lowest priority or rejecting.")
            return False

        # Expiration check
        if action.expires_at:
            try:
                if time.time() > float(action.expires_at):
                    action.status = "EXPIRED"
                    return False
            except ValueError:
                pass

        # Deduplication
        dedup_key = action.idempotency_key or f"{action.investigation_id}_{action.action_type}_{action.target_id}"
        if dedup_key in self._dedup_keys:
            logger.info(f"Duplicate action skipped in queue: {dedup_key}")
            return False

        self._dedup_keys.add(dedup_key)
        self._actions_by_id[action.action_id] = action

        # Priority ordering: HIGH/SENSITIVE first, then LOW/MEDIUM
        if action.risk_class in ("HIGH", "SENSITIVE"):
            self._queue.insert(0, action)
        else:
            self._queue.append(action)

        return True

    def pop(self) -> Optional[ProposedAction]:
        self.purge_expired()
        while self._queue:
            action = self._queue.pop(0)
            if action.status not in ("CANCELLED", "EXPIRED"):
                return action
        return None

    def cancel(self, action_id: str) -> bool:
        if action_id in self._actions_by_id:
            action = self._actions_by_id[action_id]
            action.status = "CANCELLED"
            return True
        return False

    def purge_expired(self, current_timestamp: Optional[float] = None):
        now = current_timestamp if current_timestamp is not None else time.time()
        for action in list(self._queue):
            if action.expires_at:
                try:
                    if now > float(action.expires_at):
                        action.status = "EXPIRED"
                except ValueError:
                    pass
        # Filter out cancelled/expired
        self._queue = [a for a in self._queue if a.status not in ("CANCELLED", "EXPIRED")]

    def size(self) -> int:
        return len(self._queue)
