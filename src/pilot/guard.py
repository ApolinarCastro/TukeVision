import logging
from typing import Dict, Optional
from src.pilot.contract import InferenceCoverageHealth

logger = logging.getLogger("inference_coverage_guard")

class InferenceCoverageGuard:
    """
    Monitors inference execution coverage per camera to detect and guard against
    the DEF-OBS-1 condition (active video stream flowing without model inference execution).
    """
    def __init__(self, min_frames_before_alert: int = 50):
        self.min_frames_before_alert = min_frames_before_alert
        self._camera_health: Dict[str, InferenceCoverageHealth] = {}

    def register_camera(self, camera_id: str):
        if camera_id not in self._camera_health:
            self._camera_health[camera_id] = InferenceCoverageHealth(camera_id=camera_id)

    def record_frame(self, camera_id: str):
        self.register_camera(camera_id)
        self._camera_health[camera_id].frames_received += 1
        self._evaluate_coverage(camera_id)

    def record_inference(self, camera_id: str, timestamp: str = "UNKNOWN"):
        self.register_camera(camera_id)
        self._camera_health[camera_id].inference_executed += 1
        self._camera_health[camera_id].last_inference_at = timestamp
        self._camera_health[camera_id].status = "HEALTHY"

    def _evaluate_coverage(self, camera_id: str):
        health = self._camera_health[camera_id]
        if health.frames_received >= self.min_frames_before_alert and health.inference_executed == 0:
            health.status = "ACTIVE_CAMERA_WITHOUT_INFERENCE"
            logger.warning(f"DEF-OBS-1 Guard Alert: Camera '{camera_id}' has received {health.frames_received} frames but 0 inferences were executed.")

    def get_health(self, camera_id: str) -> Optional[InferenceCoverageHealth]:
        return self._camera_health.get(camera_id)

    def check_all(self) -> Dict[str, str]:
        return {cam_id: h.status for cam_id, h in self._camera_health.items()}
