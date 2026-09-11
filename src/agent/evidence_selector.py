import logging

logger = logging.getLogger("agent_evidence")

class EvidenceSelector:
    """
    Selects the minimal required visual evidence (Key frames, ROI) to avoid
    sending massive visual streams to the VLM.
    """
    def __init__(self, max_frames: int = 3):
        self.max_frames = max_frames
        
    def select_for_investigation(self, context: dict) -> dict:
        candidate = context.get("candidate", {})
        bundle = context.get("evidence_bundle", {})
        
        frames_considered = len(bundle.get("frames", []))
        
        selection = {
            "frames_considered": frames_considered,
            "frames_selected": 0,
            "roi_selected": False,
            "selection_reason": "No evidence available",
            "selected_frames": []
        }
        
        if frames_considered == 0:
            return selection
            
        # Preference: ROI > Key Frame > Pre/Post
        # In a real implementation this would analyze motion/bounding boxes
        # Here we simulate the logic for the Cascade Architecture
        
        if candidate.get("situation_type") == "visual_ambiguity":
            selection["frames_selected"] = min(self.max_frames, frames_considered)
            selection["roi_selected"] = True
            selection["selection_reason"] = "ROI extracted around tracked entity to resolve visual ambiguity"
            # Mock the selected frames
            selection["selected_frames"] = bundle.get("frames", [])[:selection["frames_selected"]]
        else:
            # Maybe just 1 key frame
            selection["frames_selected"] = 1
            selection["roi_selected"] = False
            selection["selection_reason"] = "Single keyframe sufficient for general visual confirmation"
            selection["selected_frames"] = bundle.get("frames", [])[:1]
            
        logger.info(f"Evidence Selection: {selection['frames_selected']}/{selection['frames_considered']} frames. ROI: {selection['roi_selected']}")
        return selection
