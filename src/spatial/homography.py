"""Homography and Inverse Perspective Mapping (IPM) for Camera Calibration.

Provides the mathematical pipeline to project 2D image coordinates (like
the ground contact point of a bounding box) onto the 2D store coordinate plane
using a computed Homography matrix.
"""

from dataclasses import dataclass, field
import datetime
from typing import List, Tuple, Optional, Dict
import numpy as np
import cv2

from src.spatial.contract import StoreCoordinate

@dataclass
class CameraCalibration:
    """Configuración de calibración homográfica por cámara."""
    camera_id: str
    calibration_version: str
    image_points: List[Tuple[float, float]]
    floor_points: List[Tuple[float, float]]
    homography_matrix: Optional[np.ndarray] = None
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    validation_error: Optional[float] = None
    status: str = "UNCALIBRATED"


class HomographyEngine:
    """Motor matemático para calibrar y proyectar coordenadas mediante homografía."""

    def __init__(self):
        self._calibrations: Dict[str, CameraCalibration] = {}

    def register_calibration(
        self,
        camera_id: str,
        image_points: List[Tuple[float, float]],
        floor_points: List[Tuple[float, float]],
        version: str = "1.0"
    ) -> CameraCalibration:
        """Calcula y registra la matriz de homografía para una cámara."""
        if len(image_points) != len(floor_points):
            raise ValueError("Must have exactly the same number of image and floor points")
            
        if len(image_points) < 4:
            # Not enough points, leave uncalibrated
            calibration = CameraCalibration(
                camera_id=camera_id,
                calibration_version=version,
                image_points=image_points,
                floor_points=floor_points,
                status="UNCALIBRATED"
            )
            self._calibrations[camera_id] = calibration
            return calibration
            
        src_pts = np.array(image_points, dtype=np.float32)
        dst_pts = np.array(floor_points, dtype=np.float32)
        
        # Calculate Homography using RANSAC or standard DLT depending on points
        method = cv2.RANSAC if len(image_points) > 4 else 0
        H, mask = cv2.findHomography(src_pts, dst_pts, method)
        
        if H is None or not np.isfinite(H).all():
            calibration = CameraCalibration(
                camera_id=camera_id,
                calibration_version=version,
                image_points=image_points,
                floor_points=floor_points,
                status="DEGENERATE"
            )
            self._calibrations[camera_id] = calibration
            return calibration
            
        # Calculate Reprojection Error (Validation Error)
        projected = cv2.perspectiveTransform(src_pts.reshape(-1, 1, 2), H).reshape(-1, 2)
        error = np.mean(np.linalg.norm(dst_pts - projected, axis=1))
        
        calibration = CameraCalibration(
            camera_id=camera_id,
            calibration_version=version,
            image_points=image_points,
            floor_points=floor_points,
            homography_matrix=H,
            validation_error=float(error),
            status="CALIBRATED"
        )
        self._calibrations[camera_id] = calibration
        return calibration

    def get_calibration(self, camera_id: str) -> Optional[CameraCalibration]:
        return self._calibrations.get(camera_id)

    @staticmethod
    def estimate_foot_point(bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
        """Estima el punto de contacto (suelo) a partir de un bounding box (x1,y1,x2,y2).
        Utiliza el centro inferior del BBox.
        """
        x1, y1, x2, y2 = bbox
        return (int((x1 + x2) / 2), int(y2))

    def project_image_to_store(
        self, camera_id: str, image_x: float, image_y: float
    ) -> Optional[StoreCoordinate]:
        """Proyecta un punto de la imagen 2D al sistema métrico de la tienda."""
        calib = self._calibrations.get(camera_id)
        if calib is None or calib.status != "CALIBRATED" or calib.homography_matrix is None:
            return None
            
        pts = np.array([[[image_x, image_y]]], dtype=np.float32)
        projected = cv2.perspectiveTransform(pts, calib.homography_matrix)
        
        px, py = projected[0][0]
        return StoreCoordinate(x=float(px), y=float(py))

    def project_store_to_image(
        self, camera_id: str, store_x: float, store_y: float
    ) -> Optional[Tuple[float, float]]:
        """Proyecta de la tienda hacia la imagen (Inverse Projection)."""
        calib = self._calibrations.get(camera_id)
        if calib is None or calib.status != "CALIBRATED" or calib.homography_matrix is None:
            return None
            
        try:
            H_inv = np.linalg.inv(calib.homography_matrix)
        except np.linalg.LinAlgError:
            return None
            
        pts = np.array([[[store_x, store_y]]], dtype=np.float32)
        projected = cv2.perspectiveTransform(pts, H_inv)
        
        px, py = projected[0][0]
        return (float(px), float(py))
