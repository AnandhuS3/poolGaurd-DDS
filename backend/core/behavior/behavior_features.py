"""
Behavior Feature Extractor - Deterministic motion metrics for LSTM input
Extracts 4 key features: vertical_ratio, arm_velocity, horizontal_displacement, head_oscillation
"""

import numpy as np
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BehaviorFeatureExtractor:
    """
    Extracts deterministic motion metrics from pose keypoints
    Designed for LSTM temporal classification
    """
    
    # COCO keypoint indices
    NOSE = 0
    LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
    LEFT_WRIST, RIGHT_WRIST = 9, 10
    LEFT_HIP, RIGHT_HIP = 11, 12
    
    def __init__(self, confidence_threshold: float = 0.3):
        """
        Initialize feature extractor
        
        Args:
            confidence_threshold: Minimum confidence for keypoints
        """
        self.confidence_threshold = confidence_threshold
        self.prev_keypoints = {}  # track_id -> previous keypoints for velocity
        self.prev_features = {}  # track_id -> previous features for oscillation
    
    def extract(self, keypoints: np.ndarray, bbox: Tuple[int, int, int, int], 
                frame_height: int, track_id: Optional[int] = None) -> Optional[np.ndarray]:
        """
        Extract 4-dimensional feature vector for LSTM input
        
        Args:
            keypoints: (17, 3) array of [x, y, confidence]
            bbox: (x1, y1, x2, y2) bounding box
            frame_height: Video frame height
            track_id: Person tracking ID (for temporal features)
        
        Returns:
            4D feature vector: [vertical_ratio, arm_velocity, horizontal_displacement, head_oscillation]
            or None if insufficient keypoints
        """
        if keypoints is None or len(keypoints) < 17:
            return None
        
        # Check if enough keypoints are visible
        visible = np.sum(keypoints[:, 2] > self.confidence_threshold)
        if visible < 5:
            return None
        
        try:
            # Extract 4 features
            vertical_ratio = self._compute_vertical_ratio(keypoints, bbox, frame_height)
            arm_velocity = self._compute_arm_velocity(keypoints, track_id)
            horizontal_displacement = self._compute_horizontal_displacement(keypoints, track_id)
            head_oscillation = self._compute_head_oscillation(keypoints, track_id)
            
            # Combine into feature vector
            features = np.array([
                vertical_ratio,
                arm_velocity,
                horizontal_displacement,
                head_oscillation
            ], dtype=np.float32)
            
            # Store for next frame
            if track_id is not None:
                self.prev_keypoints[track_id] = keypoints.copy()
                self.prev_features[track_id] = features.copy()
            
            return features
            
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return None
    
    def _compute_vertical_ratio(self, keypoints: np.ndarray, 
                                bbox: Tuple[int, int, int, int], 
                                frame_height: int) -> float:
        """
        Compute vertical position ratio (0=top, 1=bottom)
        Uses hip midpoint relative to frame height
        """
        # Get hip midpoint
        left_hip = keypoints[self.LEFT_HIP]
        right_hip = keypoints[self.RIGHT_HIP]
        
        if (left_hip[2] > self.confidence_threshold and 
            right_hip[2] > self.confidence_threshold):
            hip_y = (left_hip[1] + right_hip[1]) / 2.0
        else:
            # Fallback to bbox bottom
            _, _, _, y2 = bbox
            hip_y = y2
        
        # Normalize to 0-1
        ratio = hip_y / frame_height
        return float(np.clip(ratio, 0, 1))
    
    def _compute_arm_velocity(self, keypoints: np.ndarray, 
                             track_id: Optional[int]) -> float:
        """
        Compute arm movement velocity (pixels per frame)
        Measures wrist displacement from previous frame
        """
        if track_id is None or track_id not in self.prev_keypoints:
            return 0.0
        
        prev_kp = self.prev_keypoints[track_id]
        
        # Get current and previous wrist positions
        left_wrist = keypoints[self.LEFT_WRIST]
        right_wrist = keypoints[self.RIGHT_WRIST]
        prev_left_wrist = prev_kp[self.LEFT_WRIST]
        prev_right_wrist = prev_kp[self.RIGHT_WRIST]
        
        velocities = []
        
        # Left wrist velocity
        if (left_wrist[2] > self.confidence_threshold and 
            prev_left_wrist[2] > self.confidence_threshold):
            left_vel = np.linalg.norm(left_wrist[:2] - prev_left_wrist[:2])
            velocities.append(left_vel)
        
        # Right wrist velocity
        if (right_wrist[2] > self.confidence_threshold and 
            prev_right_wrist[2] > self.confidence_threshold):
            right_vel = np.linalg.norm(right_wrist[:2] - prev_right_wrist[:2])
            velocities.append(right_vel)
        
        if not velocities:
            return 0.0
        
        # Average velocity, normalized (assume max 50 pixels/frame)
        avg_velocity = np.mean(velocities)
        normalized = avg_velocity / 50.0
        
        return float(np.clip(normalized, 0, 1))
    
    def _compute_horizontal_displacement(self, keypoints: np.ndarray, 
                                        track_id: Optional[int]) -> float:
        """
        Compute horizontal center-of-mass displacement
        Measures lateral movement from previous frame
        """
        if track_id is None or track_id not in self.prev_keypoints:
            return 0.0
        
        prev_kp = self.prev_keypoints[track_id]
        
        # Compute current center of mass
        visible_curr = keypoints[keypoints[:, 2] > self.confidence_threshold]
        visible_prev = prev_kp[prev_kp[:, 2] > self.confidence_threshold]
        
        if len(visible_curr) == 0 or len(visible_prev) == 0:
            return 0.0
        
        curr_center_x = np.mean(visible_curr[:, 0])
        prev_center_x = np.mean(visible_prev[:, 0])
        
        # Horizontal displacement
        displacement = abs(curr_center_x - prev_center_x)
        
        # Normalize (assume max 30 pixels/frame)
        normalized = displacement / 30.0
        
        return float(np.clip(normalized, 0, 1))
    
    def _compute_head_oscillation(self, keypoints: np.ndarray, 
                                  track_id: Optional[int]) -> float:
        """
        Compute head oscillation (vertical movement of nose/head)
        Indicates struggling or bobbing motion
        """
        if track_id is None or track_id not in self.prev_keypoints:
            return 0.0
        
        prev_kp = self.prev_keypoints[track_id]
        
        # Get nose position
        nose = keypoints[self.NOSE]
        prev_nose = prev_kp[self.NOSE]
        
        if (nose[2] < self.confidence_threshold or 
            prev_nose[2] < self.confidence_threshold):
            # Fallback to shoulder midpoint
            shoulder_mid = self._get_midpoint(keypoints, self.LEFT_SHOULDER, self.RIGHT_SHOULDER)
            prev_shoulder_mid = self._get_midpoint(prev_kp, self.LEFT_SHOULDER, self.RIGHT_SHOULDER)
            
            if shoulder_mid is None or prev_shoulder_mid is None:
                return 0.0
            
            vertical_movement = abs(shoulder_mid[1] - prev_shoulder_mid[1])
        else:
            vertical_movement = abs(nose[1] - prev_nose[1])
        
        # Normalize (assume max 20 pixels/frame oscillation)
        normalized = vertical_movement / 20.0
        
        return float(np.clip(normalized, 0, 1))
    
    def _get_midpoint(self, keypoints: np.ndarray, idx1: int, idx2: int) -> Optional[np.ndarray]:
        """Get midpoint between two keypoints"""
        p1, p2 = keypoints[idx1], keypoints[idx2]
        
        if (p1[2] < self.confidence_threshold or 
            p2[2] < self.confidence_threshold):
            return None
        
        return (p1[:2] + p2[:2]) / 2.0
    
    def reset_track(self, track_id: int):
        """Reset stored data for a track"""
        if track_id in self.prev_keypoints:
            del self.prev_keypoints[track_id]
        if track_id in self.prev_features:
            del self.prev_features[track_id]
    
    def reset_all(self):
        """Reset all stored data"""
        self.prev_keypoints.clear()
        self.prev_features.clear()
