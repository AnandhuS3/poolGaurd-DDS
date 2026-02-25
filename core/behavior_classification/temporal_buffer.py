"""
Temporal Buffer - Sliding window for temporal feature analysis
"""

from collections import deque
from typing import Dict, Optional, List
import numpy as np
import logging
from core.pose_estimation.pose_features import PoseFeatures

logger = logging.getLogger(__name__)


class TemporalBuffer:
    """
    Maintains sliding window of pose features for temporal analysis
    Computes statistics and patterns over time
    """
    
    def __init__(self, window_size: int = 90):
        """
        Initialize temporal buffer
        
        Args:
            window_size: Number of frames to keep in history (default: 90 = 3 sec @ 30 FPS)
        """
        self.window_size = window_size
        self.buffers: Dict[int, deque] = {}  # track_id -> deque of features
        self.frame_numbers: Dict[int, deque] = {}  # track_id -> deque of frame numbers
    
    def update(self, track_id: int, features: PoseFeatures, frame_number: int):
        """
        Add new features to buffer
        
        Args:
            track_id: Person tracking ID
            features: PoseFeatures object
            frame_number: Current frame number
        """
        if track_id not in self.buffers:
            self.buffers[track_id] = deque(maxlen=self.window_size)
            self.frame_numbers[track_id] = deque(maxlen=self.window_size)
        
        self.buffers[track_id].append(features)
        self.frame_numbers[track_id].append(frame_number)
    
    def get_statistics(self, track_id: int) -> Optional[Dict]:
        """
        Compute temporal statistics for a person
        
        Args:
            track_id: Person tracking ID
        
        Returns:
            Dictionary of temporal statistics or None if insufficient data
        """
        if track_id not in self.buffers or len(self.buffers[track_id]) < 5:
            return None
        
        features_list = list(self.buffers[track_id])
        
        try:
            stats = {
                # Orientation statistics
                'mean_vertical_angle': self._compute_mean([f.vertical_angle for f in features_list]),
                'std_vertical_angle': self._compute_std([f.vertical_angle for f in features_list]),
                
                # Position statistics
                'mean_depth_ratio': self._compute_mean([f.depth_ratio for f in features_list]),
                'std_depth_ratio': self._compute_std([f.depth_ratio for f in features_list]),
                
                # Motion statistics
                'mean_velocity': self._compute_mean([f.velocity for f in features_list]),
                'std_velocity': self._compute_std([f.velocity for f in features_list]),
                'max_velocity': max([f.velocity for f in features_list]),
                'mean_acceleration': self._compute_mean([f.acceleration for f in features_list]),
                
                # Derived statistics
                'mean_streamlined_score': self._compute_mean([f.streamlined_score for f in features_list]),
                'mean_coordination_score': self._compute_mean([f.limb_coordination for f in features_list]),
                
                # Temporal patterns
                'stillness_duration': self._compute_stillness_duration(features_list),
                'thrashing_frequency': self._compute_thrashing_frequency(features_list),
                'motion_variance': self._compute_motion_variance(features_list),
                
                # Trends
                'depth_trend': self._compute_trend([f.depth_ratio for f in features_list]),
                'velocity_trend': self._compute_trend([f.velocity for f in features_list]),
                
                # Buffer info
                'buffer_size': len(features_list),
                'frames_tracked': len(features_list)
            }
            
            return stats
            
        except Exception as e:
            logger.warning(f"Failed to compute statistics for track {track_id}: {e}")
            return None
    
    def _compute_mean(self, values: List[float]) -> float:
        """Compute mean of values"""
        if not values:
            return 0.0
        return float(np.mean(values))
    
    def _compute_std(self, values: List[float]) -> float:
        """Compute standard deviation of values"""
        if not values or len(values) < 2:
            return 0.0
        return float(np.std(values))
    
    def _compute_stillness_duration(self, features_list: List[PoseFeatures]) -> int:
        """
        Compute how many consecutive frames have minimal movement
        
        Returns:
            Number of consecutive still frames (from end of buffer)
        """
        stillness_threshold = 1.0  # pixels per frame
        
        still_count = 0
        for features in reversed(features_list):
            if features.velocity < stillness_threshold:
                still_count += 1
            else:
                break
        
        return still_count
    
    def _compute_thrashing_frequency(self, features_list: List[PoseFeatures]) -> float:
        """
        Compute thrashing frequency (rapid direction changes)
        
        Returns:
            Frequency score 0-1 (0=smooth, 1=erratic)
        """
        if len(features_list) < 3:
            return 0.0
        
        # Count direction changes in acceleration
        accelerations = [f.acceleration for f in features_list]
        
        direction_changes = 0
        for i in range(1, len(accelerations)):
            if accelerations[i] * accelerations[i-1] < 0:  # Sign change
                direction_changes += 1
        
        # Normalize by buffer size
        frequency = direction_changes / len(accelerations)
        
        return float(np.clip(frequency, 0, 1))
    
    def _compute_motion_variance(self, features_list: List[PoseFeatures]) -> float:
        """
        Compute variance in motion patterns
        High variance = erratic movement
        """
        velocities = [f.velocity for f in features_list]
        
        if len(velocities) < 2:
            return 0.0
        
        variance = np.var(velocities)
        
        # Normalize (assume max variance of 100)
        normalized_variance = variance / 100.0
        
        return float(np.clip(normalized_variance, 0, 1))
    
    def _compute_trend(self, values: List[float]) -> str:
        """
        Compute trend direction (increasing, decreasing, stable)
        
        Returns:
            'increasing', 'decreasing', or 'stable'
        """
        if len(values) < 5:
            return 'stable'
        
        # Simple linear regression slope
        x = np.arange(len(values))
        y = np.array(values)
        
        # Compute slope
        slope = np.polyfit(x, y, 1)[0]
        
        # Classify trend
        if slope > 0.01:
            return 'increasing'
        elif slope < -0.01:
            return 'decreasing'
        else:
            return 'stable'
    
    def get_buffer_size(self, track_id: int) -> int:
        """Get current buffer size for a track"""
        if track_id not in self.buffers:
            return 0
        return len(self.buffers[track_id])
    
    def clear_track(self, track_id: int):
        """Clear buffer for a specific track"""
        if track_id in self.buffers:
            del self.buffers[track_id]
        if track_id in self.frame_numbers:
            del self.frame_numbers[track_id]
    
    def clear_all(self):
        """Clear all buffers"""
        self.buffers.clear()
        self.frame_numbers.clear()
