"""
Pose Features - Feature extraction from pose keypoints
"""

import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class PoseFeatures:
    """Container for extracted pose features"""
    
    # Body orientation
    vertical_angle: float  # 0-90 degrees (0=horizontal, 90=vertical)
    face_up: bool  # True if face-up, False if face-down
    
    # Limb positions (relative to body)
    arms_above_shoulders: bool
    arms_extended: float  # 0-1 (0=collapsed, 1=extended)
    legs_spread: float  # 0-1 (0=together, 1=spread)
    legs_extended: float  # 0-1
    
    # Position in frame
    depth_ratio: float  # 0-1 (0=top, 1=bottom)
    center_x: float  # Normalized x position
    center_y: float  # Normalized y position
    
    # Motion indicators (requires temporal data)
    velocity: float  # Pixels per frame
    acceleration: float  # Change in velocity
    
    # Pose quality
    confidence: float  # Average keypoint confidence
    visible_keypoints: int  # Number of visible keypoints
    
    # Derived features
    streamlined_score: float  # 0-1 (diving pose)
    limb_coordination: float  # 0-1 (swimming coordination)
    
    # Raw data
    keypoints: Optional[np.ndarray] = None  # (17, 3) array
    bbox: Optional[tuple] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'vertical_angle': float(self.vertical_angle),
            'face_up': bool(self.face_up),
            'arms_above_shoulders': bool(self.arms_above_shoulders),
            'arms_extended': float(self.arms_extended),
            'legs_spread': float(self.legs_spread),
            'legs_extended': float(self.legs_extended),
            'depth_ratio': float(self.depth_ratio),
            'center_x': float(self.center_x),
            'center_y': float(self.center_y),
            'velocity': float(self.velocity),
            'acceleration': float(self.acceleration),
            'confidence': float(self.confidence),
            'visible_keypoints': int(self.visible_keypoints),
            'streamlined_score': float(self.streamlined_score),
            'limb_coordination': float(self.limb_coordination)
        }
