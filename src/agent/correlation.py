from typing import Dict, Any, List
from src.agent.attention_orchestrator import InvestigationCandidate

class CorrelationEngine:
    """
    Correlates Entity, Trajectory, Zone, Behavior, Handoff, Evidence, and SourceHealth
    to build an operational context without continuous video parsing.
    """
    
    def __init__(self, scene_state_getter, camera_health_getter):
        self.get_scene_state = scene_state_getter
        self.get_camera_health = camera_health_getter
        
    def correlate(self, candidate: InvestigationCandidate) -> Dict[str, Any]:
        """
        Builds a comprehensive operational situation by querying read-only tools.
        """
        context = {
            "candidate": {
                "candidate_id": candidate.candidate_id,
                "situation_type": candidate.situation_type,
                "entity_ids": candidate.entity_ids,
                "camera_ids": candidate.camera_ids,
                "zone_ids": candidate.zone_ids,
                "first_observed_at": candidate.first_observed_at,
                "last_observed_at": candidate.last_observed_at,
                "evidence_bundle_ids": candidate.evidence_bundle_ids,
            },
            "source_health": {},
            "temporal_correlations": [],
            "spatial_correlations": []
        }
        
        # 1. Source Health Awareness
        for cam_id in candidate.camera_ids:
            health = self.get_camera_health(cam_id)
            context["source_health"][cam_id] = health
            if health.get("status") != "OK":
                context["temporal_correlations"].append(
                    f"Warning: Camera {cam_id} is degraded ({health.get('status')}). Data might be incomplete."
                )

        # 2. Spatial and Temporal Correlations
        scene = self.get_scene_state()
        for entity_id in candidate.entity_ids:
            # Fake/mock correlation based on scene state logic
            entity_data = scene.get("entities", {}).get(entity_id, {})
            if "previous_zone" in entity_data:
                context["spatial_correlations"].append(
                    f"Entity {entity_id} moved from {entity_data['previous_zone']} to {candidate.zone_ids[0]}."
                )
            
        return context
