"""
Keypoint Analyzer - Extracts meaningful features from pose keypoints
"""

import numpy as np
from typing import Dict, Optional, Tuple
import logging
from .pose_features import PoseFeatures

logger = logging.getLogger(__name__)


class KeypointAnalyzer:
    """
    Analyzes pose keypoints to extract behavioral features
    """
    
    # Keypoint indices (COCO format)
    NOSE = 0
    LEFT_EYE, RIGHT_EYE = 1, 2
    LEFT_EAR, RIGHT_EAR = 3, 4
    LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
    LEFT_ELBOW, RIGHT_ELBOW = 7, 8
    LEFT_WRIST, RIGHT_WRIST = 9, 10
    LEFT_HIP, RIGHT_HIP = 11, 12
    LEFT_KNEE, RIGHT_KNEE = 13, 14
    LEFT_ANKLE, RIGHT_ANKLE = 15, 16
    
    def __init__(self, confidence_threshold: float = 0.3):
        """
        Initialize analyzer
        
        Args:
            confidence_threshold: Minimum confidence for keypoints
        """
        self.confidence_threshold = confidence_threshold
        self.prev_features = {}  # Track previous features for motion
    
    def analyze(self, pose: Dict, frame_height: int, frame_width: int, 
                track_id: Optional[int] = None) -> Optional[PoseFeatures]:
        """
        Analyze pose keypoints and extract features
        
        Args:
            pose: Pose dictionary from PoseDetector
            frame_height: Video frame height
            frame_width: Video frame width
            track_id: Person tracking ID (for temporal features)
        
        Returns:
            PoseFeatures object or None if pose unavailable
        """
        if not pose['available'] or pose['keypoints'] is None:
            return None
        
        keypoints = pose['keypoints']
        bbox = pose['bbox']
        
        # Check if enough keypoints are visible
        visible = np.sum(keypoints[:, 2] > self.confidence_threshold)
        if visible < 5:  # Need at least 5 keypoints
            return None
        
        try:
            # Extract all features
            vertical_angle = self._compute_vertical_angle(keypoints)
            face_up = self._is_face_up(keypoints)
            arms_above = self._arms_above_shoulders(keypoints)
            arms_ext = self._compute_limb_extension(keypoints, 'arms')
            legs_spread = self._compute_leg_spread(keypoints)
            legs_ext = self._compute_limb_extension(keypoints, 'legs')
            depth_ratio = self._compute_depth_ratio(keypoints, frame_height)
            center_x, center_y = self._compute_center(keypoints, frame_width, frame_height)
            confidence = self._compute_average_confidence(keypoints)
            
            # Motion features (requires previous frame)
            velocity, acceleration = self._compute_motion(keypoints, track_id)
            
            # Derived features
            streamlined = self._compute_streamlined_score(keypoints, vertical_angle, arms_ext)
            coordination = self._compute_limb_coordination(keypoints)
            
            features = PoseFeatures(
                vertical_angle=vertical_angle,
                face_up=face_up,
                arms_above_shoulders=arms_above,
                arms_extended=arms_ext,
                legs_spread=legs_spread,
                legs_extended=legs_ext,
                depth_ratio=depth_ratio,
                center_x=center_x,
                center_y=center_y,
                velocity=velocity,
                acceleration=acceleration,
                confidence=confidence,
                visible_keypoints=int(visible),
                streamlined_score=streamlined,
                limb_coordination=coordination,
                keypoints=keypoints,
                bbox=bbox
            )
            
            # Store for next frame
            if track_id is not None:
                self.prev_features[track_id] = features
            
            return features
            
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return None
    
    def _compute_vertical_angle(self, keypoints: np.ndarray) -> float:
        """
        Compute body vertical angle (0=horizontal, 90=vertical)
        Uses shoulder-hip line
        """
        # Get shoulder and hip midpoints
        shoulder_mid = self._get_midpoint(keypoints, self.LEFT_SHOULDER, self.RIGHT_SHOULDER)
        hip_mid = self._get_midpoint(keypoints, self.LEFT_HIP, self.RIGHT_HIP)
        
        if shoulder_mid is None or hip_mid is None:
            return 45.0  # Default to middle
        
        # Compute angle from horizontal
        dx = hip_mid[0] - shoulder_mid[0]
        dy = hip_mid[1] - shoulder_mid[1]
        
        angle_rad = np.arctan2(abs(dy), abs(dx))
        angle_deg = np.degrees(angle_rad)
        
        return float(angle_deg)
    
    def _is_face_up(self, keypoints: np.ndarray) -> bool:
        """
        Determine if person is face-up or face-down
        Uses nose position relative to shoulders
        """
        nose = keypoints[self.NOSE]
        shoulder_mid = self._get_midpoint(keypoints, self.LEFT_SHOULDER, self.RIGHT_SHOULDER)
        
        if nose[2] < self.confidence_threshold or shoulder_mid is None:
            return True  # Default to face-up
        
        # If nose is above shoulders, likely face-up
        return nose[1] < shoulder_mid[1]
    
    def _arms_above_shoulders(self, keypoints: np.ndarray) -> bool:
        """Check if arms are raised above shoulders"""
        shoulder_mid = self._get_midpoint(keypoints, self.LEFT_SHOULDER, self.RIGHT_SHOULDER)
        
        if shoulder_mid is None:
            return False
        
        # Check wrists
        left_wrist = keypoints[self.LEFT_WRIST]
        right_wrist = keypoints[self.RIGHT_WRIST]
        
        left_above = (left_wrist[2] > self.confidence_threshold and 
                     left_wrist[1] < shoulder_mid[1])
        right_above = (right_wrist[2] > self.confidence_threshold and 
                      right_wrist[1] < shoulder_mid[1])
        
        return left_above or right_above
    
    def _compute_limb_extension(self, keypoints: np.ndarray, limb_type: str) -> float:
        """
        Compute limb extension ratio (0=collapsed, 1=extended)
        
        Args:
            limb_type: 'arms' or 'legs'
        """
        if limb_type == 'arms':
            # Measure shoulder-elbow-wrist angle
            left_ext = self._compute_joint_extension(
                keypoints, self.LEFT_SHOULDER, self.LEFT_ELBOW, self.LEFT_WRIST
            )
            right_ext = self._compute_joint_extension(
                keypoints, self.RIGHT_SHOULDER, self.RIGHT_ELBOW, self.RIGHT_WRIST
            )
        else:  # legs
            left_ext = self._compute_joint_extension(
                keypoints, self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE
            )
            right_ext = self._compute_joint_extension(
                keypoints, self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE
            )
        
        # Average available measurements
        extensions = [e for e in [left_ext, right_ext] if e is not None]
        return float(np.mean(extensions)) if extensions else 0.5
    
    def _compute_joint_extension(self, keypoints: np.ndarray, 
                                 idx1: int, idx2: int, idx3: int) -> Optional[float]:
        """Compute extension of a 3-point joint (0=bent, 1=straight)"""
        p1, p2, p3 = keypoints[idx1], keypoints[idx2], keypoints[idx3]
        
        if (p1[2] < self.confidence_threshold or 
            p2[2] < self.confidence_threshold or 
            p3[2] < self.confidence_threshold):
            return None
        
        # Compute angle at middle joint
        v1 = p1[:2] - p2[:2]
        v2 = p3[:2] - p2[:2]
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        angle = np.arccos(np.clip(cos_angle, -1, 1))
        
        # Convert to extension ratio (180° = 1.0, 0° = 0.0)
        extension = angle / np.pi
        
        return float(extension)
    
    def _compute_leg_spread(self, keypoints: np.ndarray) -> float:
        """Compute leg spread ratio (0=together, 1=spread)"""
        left_ankle = keypoints[self.LEFT_ANKLE]
        right_ankle = keypoints[self.RIGHT_ANKLE]
        hip_mid = self._get_midpoint(keypoints, self.LEFT_HIP, self.RIGHT_HIP)
        
        if (left_ankle[2] < self.confidence_threshold or 
            right_ankle[2] < self.confidence_threshold or 
            hip_mid is None):
            return 0.5  # Default
        
        # Measure ankle distance relative to hip width
        ankle_dist = np.linalg.norm(left_ankle[:2] - right_ankle[:2])
        hip_width = np.linalg.norm(
            keypoints[self.LEFT_HIP][:2] - keypoints[self.RIGHT_HIP][:2]
        )
        
        spread_ratio = ankle_dist / (hip_width + 1e-6)
        
        # Normalize to 0-1 (assume max spread is 3x hip width)
        return float(np.clip(spread_ratio / 3.0, 0, 1))
    
    def _compute_depth_ratio(self, keypoints: np.ndarray, frame_height: int) -> float:
        """Compute vertical position in frame (0=top, 1=bottom)"""
        # Use hip midpoint as reference
        hip_mid = self._get_midpoint(keypoints, self.LEFT_HIP, self.RIGHT_HIP)
        
        if hip_mid is None:
            # Fallback to any visible keypoint
            visible = keypoints[keypoints[:, 2] > self.confidence_threshold]
            if len(visible) == 0:
                return 0.5
            hip_mid = np.mean(visible[:, :2], axis=0)
        
        depth_ratio = hip_mid[1] / frame_height
        return float(np.clip(depth_ratio, 0, 1))
    
    def _compute_center(self, keypoints: np.ndarray, 
                       frame_width: int, frame_height: int) -> Tuple[float, float]:
        """Compute normalized center of mass"""
        visible = keypoints[keypoints[:, 2] > self.confidence_threshold]
        
        if len(visible) == 0:
            return 0.5, 0.5
        
        center = np.mean(visible[:, :2], axis=0)
        
        center_x = center[0] / frame_width
        center_y = center[1] / frame_height
        
        return float(np.clip(center_x, 0, 1)), float(np.clip(center_y, 0, 1))
    
    def _compute_average_confidence(self, keypoints: np.ndarray) -> float:
        """Compute average keypoint confidence"""
        confidences = keypoints[:, 2]
        visible = confidences[confidences > self.confidence_threshold]
        
        if len(visible) == 0:
            return 0.0
        
        return float(np.mean(visible))
    
    def _compute_motion(self, keypoints: np.ndarray, 
                       track_id: Optional[int]) -> Tuple[float, float]:
        """
        Compute velocity and acceleration from previous frame
        
        Returns:
            (velocity, acceleration) in pixels per frame
        """
        if track_id is None or track_id not in self.prev_features:
            return 0.0, 0.0
        
        prev = self.prev_features[track_id]
        
        if prev.keypoints is None:
            return 0.0, 0.0
        
        # Compute center of mass displacement
        curr_center = np.mean(keypoints[keypoints[:, 2] > self.confidence_threshold, :2], axis=0)
        prev_center = np.mean(prev.keypoints[prev.keypoints[:, 2] > self.confidence_threshold, :2], axis=0)
        
        displacement = np.linalg.norm(curr_center - prev_center)
        velocity = float(displacement)
        
        # Acceleration is change in velocity
        acceleration = velocity - prev.velocity
        
        return velocity, float(acceleration)
    
    def _compute_streamlined_score(self, keypoints: np.ndarray, 
                                   vertical_angle: float, arms_extended: float) -> float:
        """
        Compute streamlined pose score (diving indicator)
        High score = arms extended forward, body horizontal
        """
        # Horizontal body (low vertical angle)
        horizontal_score = 1.0 - (vertical_angle / 90.0)
        
        # Arms extended
        arm_score = arms_extended
        
        # Combined score
        streamlined = (horizontal_score * 0.6 + arm_score * 0.4)
        
        return float(np.clip(streamlined, 0, 1))
    
    def _compute_limb_coordination(self, keypoints: np.ndarray) -> float:
        """
        Compute limb coordination score (swimming indicator)
        High score = symmetric limb positions, coordinated movement
        """
        # Check left-right symmetry
        left_arm_ext = self._compute_joint_extension(
            keypoints, self.LEFT_SHOULDER, self.LEFT_ELBOW, self.LEFT_WRIST
        )
        right_arm_ext = self._compute_joint_extension(
            keypoints, self.RIGHT_SHOULDER, self.RIGHT_ELBOW, self.RIGHT_WRIST
        )
        
        left_leg_ext = self._compute_joint_extension(
            keypoints, self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE
        )
        right_leg_ext = self._compute_joint_extension(
            keypoints, self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE
        )
        
        # Compute symmetry (1.0 = perfect symmetry)
        arm_symmetry = 1.0
        if left_arm_ext is not None and right_arm_ext is not None:
            arm_symmetry = 1.0 - abs(left_arm_ext - right_arm_ext)
        
        leg_symmetry = 1.0
        if left_leg_ext is not None and right_leg_ext is not None:
            leg_symmetry = 1.0 - abs(left_leg_ext - right_leg_ext)
        
        # Combined coordination score
        coordination = (arm_symmetry + leg_symmetry) / 2.0
        
        return float(np.clip(coordination, 0, 1))
    
    def _get_midpoint(self, keypoints: np.ndarray, idx1: int, idx2: int) -> Optional[np.ndarray]:
        """Get midpoint between two keypoints"""
        p1, p2 = keypoints[idx1], keypoints[idx2]
        
        if (p1[2] < self.confidence_threshold or 
            p2[2] < self.confidence_threshold):
            return None
        
        return (p1[:2] + p2[:2]) / 2.0
