"""
Behavior Classifier - Classifies behavior based on pose features and temporal patterns
"""

import logging
from typing import Optional, Dict
from core.pose_estimation.pose_features import PoseFeatures
from .behavior_patterns import BehaviorType, BehaviorPattern, BEHAVIOR_PATTERNS

logger = logging.getLogger(__name__)


class BehaviorClassifier:
    """
    Classifies person behavior using rule-based logic
    Combines pose features and temporal statistics
    """
    
    def __init__(self):
        """Initialize classifier"""
        self.patterns = BEHAVIOR_PATTERNS
    
    def classify(self, features: PoseFeatures, temporal_stats: Optional[Dict] = None) -> BehaviorType:
        """
        Classify behavior based on features and temporal statistics
        
        Args:
            features: Current pose features
            temporal_stats: Temporal statistics from TemporalBuffer
        
        Returns:
            BehaviorType enum
        """
        if features is None:
            return BehaviorType.UNKNOWN
        
        # If no temporal data, use simple classification
        if temporal_stats is None or temporal_stats.get('buffer_size', 0) < 5:
            return self._classify_instant(features)
        
        # Full classification with temporal context
        return self._classify_temporal(features, temporal_stats)
    
    def _classify_instant(self, features: PoseFeatures) -> BehaviorType:
        """
        Classify based on instant features only (no temporal data)
        Used for first few frames
        """
        # Check for diving (streamlined pose)
        if features.streamlined_score > 0.7:
            return BehaviorType.DIVING
        
        # Check for drowning: must be deep AND nearly vertical (avoids false alarm
        # for people standing at the bottom of the camera frame on land which also
        # yields a high depth_ratio but stay horizontal/walking)
        if features.depth_ratio > 0.7 and features.vertical_angle > 50:
            return BehaviorType.DROWNING
        
        # Check for vertical orientation (potential struggling)
        # Require they also be at some depth (not just standing upright on land)
        if features.vertical_angle > 60 and features.depth_ratio > 0.35:
            return BehaviorType.STRUGGLING
        
        # Default to swimming (safe)
        return BehaviorType.SWIMMING
    
    def _classify_temporal(self, features: PoseFeatures, stats: Dict) -> BehaviorType:
        """
        Classify with full temporal context
        Uses decision tree based on behavior patterns
        """
        # Priority 1: Check for DROWNING (most critical)
        if self._matches_pattern(features, stats, BehaviorType.DROWNING):
            return BehaviorType.DROWNING
        
        # Priority 2: Check for STRUGGLING
        if self._matches_pattern(features, stats, BehaviorType.STRUGGLING):
            return BehaviorType.STRUGGLING
        
        # Priority 3: Check for DIVING (intentional submersion)
        if self._matches_pattern(features, stats, BehaviorType.DIVING):
            return BehaviorType.DIVING
        
        # Priority 4: Check for FLOATING
        if self._matches_pattern(features, stats, BehaviorType.FLOATING):
            return BehaviorType.FLOATING
        
        # Priority 5: Check for SWIMMING
        if self._matches_pattern(features, stats, BehaviorType.SWIMMING):
            return BehaviorType.SWIMMING
        
        # Default
        return BehaviorType.UNKNOWN
    
    def _matches_pattern(self, features: PoseFeatures, stats: Dict, 
                        behavior_type: BehaviorType) -> bool:
        """
        Check if features/stats match a behavior pattern
        
        Args:
            features: Current pose features
            stats: Temporal statistics
            behavior_type: Pattern to check
        
        Returns:
            True if pattern matches
        """
        pattern = self.patterns.get(behavior_type)
        if pattern is None:
            return False
        
        # Check pose feature thresholds
        if not (pattern.min_vertical_angle <= features.vertical_angle <= pattern.max_vertical_angle):
            return False
        
        if not (pattern.min_depth_ratio <= features.depth_ratio <= pattern.max_depth_ratio):
            return False
        
        if features.streamlined_score < pattern.min_streamlined_score:
            return False
        
        if features.limb_coordination < pattern.min_coordination_score:
            return False
        
        # Check temporal thresholds
        mean_velocity = stats.get('mean_velocity', 0.0)
        if not (pattern.min_velocity <= mean_velocity <= pattern.max_velocity):
            return False
        
        stillness = stats.get('stillness_duration', 0)
        if not (pattern.min_stillness_duration <= stillness <= pattern.max_stillness_duration):
            return False
        
        thrashing = stats.get('thrashing_frequency', 0.0)
        if thrashing < pattern.min_thrashing_frequency:
            return False
        
        # Check boolean criteria
        if pattern.requires_face_down and features.face_up:
            return False
        
        if pattern.requires_arms_above and not features.arms_above_shoulders:
            return False
        
        # All criteria matched
        return True
    
    def get_confidence(self, features: PoseFeatures, stats: Optional[Dict], 
                      behavior_type: BehaviorType) -> float:
        """
        Compute confidence score for a classification
        
        Args:
            features: Pose features
            stats: Temporal statistics
            behavior_type: Classified behavior
        
        Returns:
            Confidence score 0-1
        """
        if features is None:
            return 0.0
        
        # Base confidence on pose quality
        base_confidence = features.confidence
        
        # Boost confidence if temporal data available
        if stats is not None and stats.get('buffer_size', 0) >= 30:
            temporal_boost = 0.2
        elif stats is not None and stats.get('buffer_size', 0) >= 10:
            temporal_boost = 0.1
        else:
            temporal_boost = 0.0
        
        # Boost confidence if pattern strongly matches
        if stats is not None and self._matches_pattern(features, stats, behavior_type):
            pattern_boost = 0.1
        else:
            pattern_boost = 0.0
        
        total_confidence = min(1.0, base_confidence + temporal_boost + pattern_boost)
        
        return float(total_confidence)
