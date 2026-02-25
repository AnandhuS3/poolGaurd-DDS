"""
Pose-Driven Video Processing Integration
This module integrates the new pose-driven pipeline with the existing process_video.py
"""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple, List
import logging

# Import pose estimation components
from core.pose_estimation import PoseDetector, KeypointAnalyzer
from core.behavior_classification import (
    TemporalBuffer, BehaviorClassifier, StateMachine, 
    BehaviorType, PersonState
)

logger = logging.getLogger(__name__)


class PoseDrivenProcessor:
    """
    Wrapper for pose-driven drowning detection pipeline
    Integrates with existing YOLO + DeepSORT tracking
    """
    
    def __init__(self, config):
        """
        Initialize pose-driven processor
        
        Args:
            config: Configuration module with all settings
        """
        self.config = config
        self.enabled = getattr(config, 'USE_POSE_ESTIMATION', False)
        self.fallback_enabled = getattr(config, 'FALLBACK_TO_HEURISTIC', True)
        
        # Initialize components
        self.pose_detector = None
        self.keypoint_analyzer = None
        self.temporal_buffer = None
        self.behavior_classifier = None
        self.state_machine = None
        
        if self.enabled:
            self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all pose-driven components"""
        try:
            # Pose detection
            model_type = getattr(self.config, 'POSE_MODEL_TYPE', 'yolov8-pose')
            model_path = getattr(self.config, 'POSE_MODEL_PATH', None)
            pose_conf = getattr(self.config, 'POSE_CONFIDENCE_THRESHOLD', 0.3)
            
            self.pose_detector = PoseDetector(
                model_type=model_type,
                model_path=str(model_path) if model_path else None,
                confidence_threshold=pose_conf
            )
            
            # Keypoint analysis
            self.keypoint_analyzer = KeypointAnalyzer(
                confidence_threshold=pose_conf
            )
            
            # Temporal buffer
            window_size = getattr(self.config, 'TEMPORAL_WINDOW_SIZE', 90)
            self.temporal_buffer = TemporalBuffer(window_size=window_size)
            
            # Behavior classifier
            self.behavior_classifier = BehaviorClassifier()
            
            # State machine
            attention_thresh = getattr(self.config, 'ATTENTION_THRESHOLD', 15)
            warning_thresh = getattr(self.config, 'WARNING_THRESHOLD', 30)
            danger_thresh = getattr(self.config, 'DANGER_THRESHOLD', 60)
            
            self.state_machine = StateMachine(
                attention_threshold=attention_thresh,
                warning_threshold=warning_thresh,
                danger_threshold=danger_thresh
            )
            
            # Check if pose detector is available
            if not self.pose_detector.is_available():
                logger.warning("Pose detector not available - will use fallback")
                self.enabled = False
            else:
                logger.info("✅ Pose-driven pipeline initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize pose-driven pipeline: {e}")
            logger.info("Falling back to heuristic detection")
            self.enabled = False
    
    def process_tracks(self, frame: np.ndarray, tracks: List, 
                      frame_number: int, frame_height: int, frame_width: int) -> Dict:
        """
        Process tracked persons with pose-driven analysis
        
        Args:
            frame: Current video frame
            tracks: DeepSORT tracks
            frame_number: Current frame number
            frame_height: Frame height
            frame_width: Frame width
        
        Returns:
            Dictionary mapping track_id to analysis results:
            {
                track_id: {
                    'state': PersonState,
                    'behavior': BehaviorType,
                    'confidence': float,
                    'pose_available': bool,
                    'features': dict (optional)
                }
            }
        """
        if not self.enabled or not self.pose_detector.is_available():
            return {}
        
        results = {}
        
        # Extract bounding boxes for all confirmed tracks
        bboxes = []
        track_ids = []
        
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            ltrb = track.to_ltrb()
            x1, y1, x2, y2 = map(int, ltrb)
            bboxes.append((x1, y1, x2, y2))
            track_ids.append(track.track_id)
        
        if len(bboxes) == 0:
            return results
        
        # Detect poses for all persons
        poses = self.pose_detector.detect_poses(frame, bboxes)
        
        # Analyze each pose
        for track_id, pose in zip(track_ids, poses):
            try:
                # Extract features from pose
                features = self.keypoint_analyzer.analyze(
                    pose, frame_height, frame_width, track_id
                )
                
                if features is None:
                    results[track_id] = {
                        'state': PersonState.SAFE,
                        'behavior': BehaviorType.UNKNOWN,
                        'confidence': 0.0,
                        'pose_available': False
                    }
                    continue
                
                # Update temporal buffer
                self.temporal_buffer.update(track_id, features, frame_number)
                
                # Get temporal statistics
                temporal_stats = self.temporal_buffer.get_statistics(track_id)
                
                # Classify behavior
                behavior = self.behavior_classifier.classify(features, temporal_stats)
                
                # Update state machine
                state = self.state_machine.update(track_id, behavior, frame_number)
                
                # Compute confidence
                confidence = self.behavior_classifier.get_confidence(
                    features, temporal_stats, behavior
                )
                
                results[track_id] = {
                    'state': state,
                    'behavior': behavior,
                    'confidence': confidence,
                    'pose_available': True,
                    'features': features.to_dict() if features else None,
                    'temporal_stats': temporal_stats
                }
                
            except Exception as e:
                logger.warning(f"Failed to process track {track_id}: {e}")
                results[track_id] = {
                    'state': PersonState.SAFE,
                    'behavior': BehaviorType.UNKNOWN,
                    'confidence': 0.0,
                    'pose_available': False
                }
        
        return results
    
    def visualize_pose(self, frame: np.ndarray, track_id: int, 
                      bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Visualize pose on frame (debug mode)
        
        Args:
            frame: Video frame
            track_id: Person tracking ID
            bbox: Bounding box (x1, y1, x2, y2)
        
        Returns:
            Frame with pose overlay
        """
        if not self.enabled or not self.pose_detector.is_available():
            return frame
        
        visualize = getattr(self.config, 'VISUALIZE_POSE', False)
        if not visualize:
            return frame
        
        # Detect pose for this person
        poses = self.pose_detector.detect_poses(frame, [bbox])
        
        if len(poses) > 0:
            frame = self.pose_detector.visualize_pose(frame, poses[0])
        
        return frame
    
    def is_available(self) -> bool:
        """Check if pose-driven pipeline is available"""
        return self.enabled and self.pose_detector is not None and self.pose_detector.is_available()
    
    def reset(self):
        """Reset all buffers and state"""
        if self.temporal_buffer:
            self.temporal_buffer.clear_all()
        if self.state_machine:
            self.state_machine.reset_all()
