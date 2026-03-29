"""
Behavior Patterns - Definitions for different swimming/drowning behaviors
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict


class BehaviorType(Enum):
    """Types of behaviors that can be detected"""
    SWIMMING = "swimming"
    DIVING = "diving"
    FLOATING = "floating"
    STRUGGLING = "struggling"
    DROWNING = "drowning"
    UNKNOWN = "unknown"


@dataclass
class BehaviorPattern:
    """
    Pattern definition for a specific behavior
    Contains thresholds and criteria for classification
    """
    behavior_type: BehaviorType
    
    # Pose feature thresholds
    min_vertical_angle: float = 0.0
    max_vertical_angle: float = 90.0
    min_depth_ratio: float = 0.0
    max_depth_ratio: float = 1.0
    min_streamlined_score: float = 0.0
    min_coordination_score: float = 0.0
    
    # Temporal thresholds
    min_velocity: float = 0.0
    max_velocity: float = float('inf')
    min_stillness_duration: int = 0  # frames
    max_stillness_duration: int = 999999
    min_thrashing_frequency: float = 0.0
    
    # Other criteria
    requires_face_down: bool = False
    requires_arms_above: bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'behavior_type': self.behavior_type.value,
            'min_vertical_angle': self.min_vertical_angle,
            'max_vertical_angle': self.max_vertical_angle,
            'min_depth_ratio': self.min_depth_ratio,
            'max_depth_ratio': self.max_depth_ratio,
            'min_streamlined_score': self.min_streamlined_score,
            'min_coordination_score': self.min_coordination_score,
            'min_velocity': self.min_velocity,
            'max_velocity': self.max_velocity,
            'min_stillness_duration': self.min_stillness_duration,
            'max_stillness_duration': self.max_stillness_duration,
            'min_thrashing_frequency': self.min_thrashing_frequency,
            'requires_face_down': self.requires_face_down,
            'requires_arms_above': self.requires_arms_above
        }


# Predefined behavior patterns
BEHAVIOR_PATTERNS = {
    BehaviorType.SWIMMING: BehaviorPattern(
        behavior_type=BehaviorType.SWIMMING,
        min_vertical_angle=0.0,
        max_vertical_angle=45.0,  # Mostly horizontal
        min_depth_ratio=0.3,
        max_depth_ratio=0.8,
        min_coordination_score=0.6,  # Coordinated movement
        min_velocity=2.0,  # Active movement
        max_stillness_duration=30  # Not still for long
    ),
    
    BehaviorType.DIVING: BehaviorPattern(
        behavior_type=BehaviorType.DIVING,
        min_vertical_angle=0.0,
        max_vertical_angle=30.0,  # Very horizontal
        min_streamlined_score=0.7,  # Streamlined pose
        min_velocity=3.0,  # Fast movement
        max_stillness_duration=15
    ),
    
    BehaviorType.FLOATING: BehaviorPattern(
        behavior_type=BehaviorType.FLOATING,
        min_vertical_angle=0.0,
        max_vertical_angle=45.0,
        min_depth_ratio=0.2,
        max_depth_ratio=0.7,
        max_velocity=1.0,  # Minimal movement
        min_stillness_duration=30,  # Relatively still
        min_thrashing_frequency=0.0,
        requires_face_down=False
    ),
    
    BehaviorType.STRUGGLING: BehaviorPattern(
        behavior_type=BehaviorType.STRUGGLING,
        min_vertical_angle=40.0,   # More vertical posture (lowered from 45)
        max_vertical_angle=90.0,
        min_depth_ratio=0.35,      # Lowered: catch person just fallen into pool (mid-frame)
        max_depth_ratio=1.0,
        min_thrashing_frequency=0.3,  # Erratic movement (lowered from 0.4)
        max_stillness_duration=25,
        # Removed requires_arms_above=True — unreliable from overhead/angled cameras
    ),
    
    BehaviorType.DROWNING: BehaviorPattern(
        behavior_type=BehaviorType.DROWNING,
        min_vertical_angle=30.0,
        max_vertical_angle=90.0,
        min_depth_ratio=0.55,      # Slightly reduced (was 0.6) to detect earlier
        max_depth_ratio=1.0,
        max_velocity=1.0,          # Raised slightly (was 0.5) — some movement may still be present
        min_stillness_duration=45, # Reduced (was 60) — detect drowning sooner
        # Removed requires_face_down=True — face orientation unreliable from overhead cameras
    )
}


def get_pattern(behavior_type: BehaviorType) -> BehaviorPattern:
    """Get predefined pattern for a behavior type"""
    return BEHAVIOR_PATTERNS.get(behavior_type, BehaviorPattern(BehaviorType.UNKNOWN))
