"""
Risk Inference Engine - Real-time temporal inference with rolling buffers
Maintains 3-second keypoint/feature buffers per track and computes softmax risk scores
"""

import torch
import numpy as np
from collections import deque
from typing import Dict, Optional, Tuple
import logging
from .temporal_model import TemporalLSTMClassifier, LSTMModelLoader
from .behavior_features import BehaviorFeatureExtractor

logger = logging.getLogger(__name__)


class TrackBuffer:
    """
    Rolling buffer for a single track
    Maintains 3-second history of keypoints and features
    """
    
    def __init__(self, buffer_size: int = 90):
        """
        Initialize track buffer
        
        Args:
            buffer_size: Number of frames to keep (default: 90 = 3 sec @ 30 FPS)
        """
        self.buffer_size = buffer_size
        self.keypoints_buffer = deque(maxlen=buffer_size)
        self.features_buffer = deque(maxlen=buffer_size)
        self.frame_numbers = deque(maxlen=buffer_size)
        self.risk_state = "SAFE"  # Current risk state
        self.risk_scores = np.array([1.0, 0.0, 0.0])  # [SAFE, WARNING, DANGER]
    
    def add(self, keypoints: np.ndarray, features: np.ndarray, frame_number: int):
        """Add new data to buffer"""
        self.keypoints_buffer.append(keypoints.copy())
        self.features_buffer.append(features.copy())
        self.frame_numbers.append(frame_number)
    
    def get_feature_sequence(self) -> Optional[np.ndarray]:
        """
        Get feature sequence for LSTM input
        
        Returns:
            (sequence_length, 4) array or None if insufficient data
        """
        if len(self.features_buffer) == 0:
            return None
        
        # Stack features into sequence
        sequence = np.stack(list(self.features_buffer), axis=0)
        return sequence
    
    def is_ready(self, min_frames: int = 30) -> bool:
        """Check if buffer has enough frames for inference"""
        return len(self.features_buffer) >= min_frames
    
    def update_risk(self, risk_class: int, risk_scores: np.ndarray):
        """Update risk state and scores"""
        state_map = {0: "SAFE", 1: "WARNING", 2: "DANGER"}
        self.risk_state = state_map.get(risk_class, "SAFE")
        self.risk_scores = risk_scores.copy()


class RiskInferenceEngine:
    """
    Real-time risk inference engine
    Manages per-track buffers and LSTM inference
    """
    
    def __init__(self, model_path: Optional[str] = None, 
                 buffer_size: int = 90, 
                 min_frames: int = 30,
                 device: str = 'cpu'):
        """
        Initialize inference engine
        
        Args:
            model_path: Path to LSTM weights
            buffer_size: Rolling buffer size (frames)
            min_frames: Minimum frames before inference
            device: 'cpu' or 'cuda'
        """
        self.buffer_size = buffer_size
        self.min_frames = min_frames
        self.device = device
        
        # Track buffers
        self.track_buffers: Dict[int, TrackBuffer] = {}
        
        # Feature extractor
        self.feature_extractor = BehaviorFeatureExtractor()
        
        # Load LSTM model
        self.model_loader = LSTMModelLoader(model_path, device)
        self.model = None
        self.model_available = False
        
        if model_path:
            self.model_available = self.model_loader.load()
            if self.model_available:
                self.model = self.model_loader.get_model()
    
    def process_track(self, track_id: int, keypoints: np.ndarray, 
                     bbox: Tuple[int, int, int, int], 
                     frame_height: int, frame_number: int) -> Dict:
        """
        Process a single track with pose keypoints
        
        Args:
            track_id: Person tracking ID
            keypoints: (17, 3) pose keypoints
            bbox: (x1, y1, x2, y2) bounding box
            frame_height: Video frame height
            frame_number: Current frame number
        
        Returns:
            Dictionary with risk assessment:
            {
                'risk_state': 'SAFE'|'WARNING'|'DANGER',
                'risk_scores': [safe_prob, warning_prob, danger_prob],
                'confidence': float,
                'buffer_size': int,
                'inference_ready': bool
            }
        """
        # Initialize buffer if new track
        if track_id not in self.track_buffers:
            self.track_buffers[track_id] = TrackBuffer(self.buffer_size)
        
        buffer = self.track_buffers[track_id]
        
        # Extract features
        features = self.feature_extractor.extract(
            keypoints, bbox, frame_height, track_id
        )
        
        if features is None:
            # Return current state if feature extraction fails
            return {
                'risk_state': buffer.risk_state,
                'risk_scores': buffer.risk_scores.tolist(),
                'confidence': float(np.max(buffer.risk_scores)),
                'buffer_size': len(buffer.features_buffer),
                'inference_ready': False
            }
        
        # Add to buffer
        buffer.add(keypoints, features, frame_number)
        
        # Run inference if ready and model available
        if buffer.is_ready(self.min_frames) and self.model_available:
            risk_class, risk_scores = self._run_inference(buffer)
            buffer.update_risk(risk_class, risk_scores)
        
        # Return risk assessment
        return {
            'risk_state': buffer.risk_state,
            'risk_scores': buffer.risk_scores.tolist(),
            'confidence': float(np.max(buffer.risk_scores)),
            'buffer_size': len(buffer.features_buffer),
            'inference_ready': buffer.is_ready(self.min_frames)
        }
    
    def _run_inference(self, buffer: TrackBuffer) -> Tuple[int, np.ndarray]:
        """
        Run LSTM inference on buffer
        
        Args:
            buffer: TrackBuffer with feature sequence
        
        Returns:
            (predicted_class, risk_scores)
        """
        if self.model is None:
            # Fallback to safe state
            return 0, np.array([1.0, 0.0, 0.0])
        
        try:
            # Get feature sequence
            sequence = buffer.get_feature_sequence()
            
            if sequence is None or len(sequence) < self.min_frames:
                return 0, np.array([1.0, 0.0, 0.0])
            
            # Convert to tensor
            sequence_tensor = torch.from_numpy(sequence).float().unsqueeze(0)  # (1, seq_len, 4)
            sequence_tensor = sequence_tensor.to(self.device)
            
            # Run inference
            predicted_class, risk_scores = self.model.predict(sequence_tensor)
            
            return predicted_class, risk_scores
            
        except Exception as e:
            logger.warning(f"LSTM inference failed: {e}")
            return 0, np.array([1.0, 0.0, 0.0])
    
    def get_track_state(self, track_id: int) -> Dict:
        """Get current risk state for a track"""
        if track_id not in self.track_buffers:
            return {
                'risk_state': 'SAFE',
                'risk_scores': [1.0, 0.0, 0.0],
                'confidence': 1.0,
                'buffer_size': 0,
                'inference_ready': False
            }
        
        buffer = self.track_buffers[track_id]
        return {
            'risk_state': buffer.risk_state,
            'risk_scores': buffer.risk_scores.tolist(),
            'confidence': float(np.max(buffer.risk_scores)),
            'buffer_size': len(buffer.features_buffer),
            'inference_ready': buffer.is_ready(self.min_frames)
        }
    
    def reset_track(self, track_id: int):
        """Reset buffer for a track"""
        if track_id in self.track_buffers:
            del self.track_buffers[track_id]
        self.feature_extractor.reset_track(track_id)
    
    def reset_all(self):
        """Reset all track buffers"""
        self.track_buffers.clear()
        self.feature_extractor.reset_all()
    
    def is_available(self) -> bool:
        """Check if inference engine is available"""
        return self.model_available
