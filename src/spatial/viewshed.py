"""Camera Coverage and Viewshed Engine.

Calculates spatial visibility, occlusions, and coverage gaps based on
store geometry and camera models.
"""

from typing import List, Dict, Optional, Tuple
from enum import Enum
import numpy as np
import cv2
import logging

from src.spatial.contract import StoreCoordinate, CameraSpatialModel

logger = logging.getLogger("tukevision.spatial.viewshed")

class VisibilityState(str, Enum):
    VISIBLE = "VISIBLE"
    OCCLUDED = "OCCLUDED"
    OUTSIDE_COVERAGE = "OUTSIDE_COVERAGE"
    UNKNOWN = "UNKNOWN"

class ViewshedEngine:
    def __init__(self, resolution_px_per_m: float = 10.0):
        self._cameras: Dict[str, CameraSpatialModel] = {}
        self._store_floor: Optional[List[StoreCoordinate]] = None
        self._resolution = resolution_px_per_m  # For rasterization

    def set_store_floor(self, polygon: List[StoreCoordinate]):
        """Define the geometric boundary of the store."""
        self._store_floor = polygon

    def add_camera_model(self, model: CameraSpatialModel):
        self._cameras[model.camera_id] = model

    def get_camera_coverage(self, camera_id: str) -> Optional[CameraSpatialModel]:
        return self._cameras.get(camera_id)

    def check_visibility(self, x: float, y: float, camera_id: Optional[str] = None) -> VisibilityState:
        """Check if a specific point is visible by a camera (or any camera)."""
        pt = (float(x), float(y))
        
        # Check specific camera
        if camera_id:
            cam = self._cameras.get(camera_id)
            if not cam or not cam.coverage.is_active:
                return VisibilityState.UNKNOWN
                
            pts = np.array([[p.x, p.y] for p in cam.coverage.polygon_points], dtype=np.float32)
            if cv2.pointPolygonTest(pts, pt, False) >= 0:
                # Check occlusions
                if cam.occlusion_model:
                    for occ in cam.occlusion_model:
                        opts = np.array([[p.x, p.y] for p in occ], dtype=np.float32)
                        if cv2.pointPolygonTest(opts, pt, False) >= 0:
                            return VisibilityState.OCCLUDED
                return VisibilityState.VISIBLE
            return VisibilityState.OUTSIDE_COVERAGE
            
        # Check any camera
        if not self._cameras:
            return VisibilityState.UNKNOWN
            
        is_outside = True
        for cam_id in self._cameras:
            state = self.check_visibility(x, y, cam_id)
            if state == VisibilityState.VISIBLE:
                return VisibilityState.VISIBLE
            if state == VisibilityState.OCCLUDED:
                is_outside = False  # It's inside a camera's FOV but occluded
                
        return VisibilityState.OUTSIDE_COVERAGE if is_outside else VisibilityState.OCCLUDED

    def get_coverage_gaps(self) -> List[List[StoreCoordinate]]:
        """Calculate store floor areas not covered by any active camera.
        Uses a rasterization approach to avoid complex polygon math dependencies.
        """
        if not self._store_floor:
            return []
            
        # 1. Find bounding box of the store
        xs = [p.x for p in self._store_floor]
        ys = [p.y for p in self._store_floor]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        # Add padding
        pad = 2.0
        min_x, max_x = min_x - pad, max_x + pad
        min_y, max_y = min_y - pad, max_y + pad
        
        width_m = max_x - min_x
        height_m = max_y - min_y
        
        if width_m <= 0 or height_m <= 0:
            return []
            
        # 2. Create discrete mask
        w_px = int(width_m * self._resolution)
        h_px = int(height_m * self._resolution)
        
        if w_px == 0 or h_px == 0:
            return []
            
        # Store mask (white = inside store)
        store_mask = np.zeros((h_px, w_px), dtype=np.uint8)
        store_pts = np.array([
            [int((p.x - min_x) * self._resolution), int((p.y - min_y) * self._resolution)]
            for p in self._store_floor
        ], dtype=np.int32)
        cv2.fillPoly(store_mask, [store_pts], 255)
        
        # Coverage mask (white = covered)
        cov_mask = np.zeros((h_px, w_px), dtype=np.uint8)
        for cam in self._cameras.values():
            if not cam.coverage.is_active:
                continue
            cam_pts = np.array([
                [int((p.x - min_x) * self._resolution), int((p.y - min_y) * self._resolution)]
                for p in cam.coverage.polygon_points
            ], dtype=np.int32)
            cv2.fillPoly(cov_mask, [cam_pts], 255)
            
            # Remove occlusions from coverage
            if cam.occlusion_model:
                for occ in cam.occlusion_model:
                    opts = np.array([
                        [int((p.x - min_x) * self._resolution), int((p.y - min_y) * self._resolution)]
                        for p in occ
                    ], dtype=np.int32)
                    cv2.fillPoly(cov_mask, [opts], 0)
        
        # 3. Gaps = Store AND NOT Coverage
        gaps_mask = cv2.bitwise_and(store_mask, cv2.bitwise_not(cov_mask))
        
        # 4. Extract contours of gaps
        contours, _ = cv2.findContours(gaps_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        gaps = []
        for contour in contours:
            # Filter tiny artifacts
            if cv2.contourArea(contour) < (0.5 * self._resolution * self._resolution): # e.g. < 0.5 sq meters
                continue
            
            gap_poly = []
            # Simplify contour slightly
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            for pt in approx:
                px, py = pt[0]
                sx = (px / self._resolution) + min_x
                sy = (py / self._resolution) + min_y
                gap_poly.append(StoreCoordinate(x=sx, y=sy))
            if gap_poly:
                gaps.append(gap_poly)
                
        return gaps
