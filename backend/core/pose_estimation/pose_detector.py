"""
Pose Detector - Extracts human pose keypoints from video frames
Supports YOLOv8-pose and MediaPipe backends
"""

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class PoseDetector:
    """
    Detects and extracts pose keypoints from person bounding boxes
    
    COCO Keypoint Format (17 points):
    0: nose, 1-2: eyes, 3-4: ears, 5-6: shoulders,
    7-8: elbows, 9-10: wrists, 11-12: hips,
    13-14: knees, 15-16: ankles
    """
    
    KEYPOINT_NAMES = [
        'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
        'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
        'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
        'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
    ]
    
    def __init__(self, model_type: str = "yolov8-pose", model_path: Optional[str] = None, 
                 confidence_threshold: float = 0.3, device: str = 'auto'):
        """
        Initialize pose detector
        
        Args:
            model_type: "yolov8-pose" or "mediapipe"
            model_path: Path to pose model weights
            confidence_threshold: Minimum confidence for keypoints
            device: 'auto', 'cpu', or 'cuda' - device for inference
        """
        self.model_type = model_type
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.model = None
        self.available = False
        
        try:
            if model_type == "yolov8-pose":
                self._init_yolo_pose(model_path)
            elif model_type == "mediapipe":
                self._init_mediapipe()
            else:
                logger.warning(f"Unknown pose model type: {model_type}")
        except Exception as e:
            logger.error(f"Failed to initialize pose detector: {e}")
            logger.info("Pose estimation will be disabled")
    
    def _init_yolo_pose(self, model_path: Optional[str]):
        """Initialize YOLOv8-pose model"""
        try:
            from ultralytics import YOLO
            
            # Use provided path or default to yolov8n-pose
            if model_path is None:
                model_path = "yolov8n-pose.pt"
            
            self.model = YOLO(model_path)
            
            # Set device
            import torch
            if self.device == 'auto':
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
            else:
                device = self.device
            
            self.model.to(device)
            
            self.available = True
            logger.info(f"YOLOv8-pose initialized on {device}")
            
        except ImportError:
            logger.error("ultralytics not installed. Install with: pip install ultralytics")
        except Exception as e:
            logger.error(f"Failed to load YOLOv8-pose: {e}")
    
    def _init_mediapipe(self):
        """Initialize MediaPipe Pose"""
        try:
            import mediapipe as mp
            
            self.mp_pose = mp.solutions.pose
            self.model = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=self.confidence_threshold,
                min_tracking_confidence=self.confidence_threshold
            )
            
            self.available = True
            logger.info("MediaPipe Pose initialized")
            
        except ImportError:
            logger.error("mediapipe not installed. Install with: pip install mediapipe")
        except Exception as e:
            logger.error(f"Failed to load MediaPipe: {e}")
    
    def detect_poses(self, frame: np.ndarray, bboxes: List[Tuple[int, int, int, int]]) -> List[Dict]:
        """
        Detect poses for all person bounding boxes
        
        Args:
            frame: Full video frame (BGR)
            bboxes: List of bounding boxes [(x1, y1, x2, y2), ...]
        
        Returns:
            List of pose dictionaries, one per bbox:
            {
                'keypoints': np.ndarray (17, 3) - [x, y, confidence],
                'bbox': (x1, y1, x2, y2),
                'available': bool
            }
        """
        if not self.available:
            return [{'keypoints': None, 'bbox': bbox, 'available': False} for bbox in bboxes]
        
        poses = []
        
        for bbox in bboxes:
            try:
                pose = self._detect_single_pose(frame, bbox)
                poses.append(pose)
            except Exception as e:
                logger.warning(f"Pose detection failed for bbox {bbox}: {e}")
                poses.append({'keypoints': None, 'bbox': bbox, 'available': False})
        
        return poses
    
    def _detect_single_pose(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Dict:
        """Detect pose for a single person bounding box"""
        x1, y1, x2, y2 = bbox
        
        # Crop person region
        person_crop = frame[y1:y2, x1:x2]
        
        if person_crop.size == 0:
            return {'keypoints': None, 'bbox': bbox, 'available': False}
        
        if self.model_type == "yolov8-pose":
            return self._detect_yolo_pose(person_crop, bbox)
        elif self.model_type == "mediapipe":
            return self._detect_mediapipe_pose(person_crop, bbox)
        else:
            return {'keypoints': None, 'bbox': bbox, 'available': False}
    
    def _detect_yolo_pose(self, person_crop: np.ndarray, bbox: Tuple[int, int, int, int]) -> Dict:
        """Detect pose using YOLOv8-pose"""
        x1, y1, x2, y2 = bbox
        
        # Run inference
        results = self.model(person_crop, verbose=False)
        
        if len(results) == 0 or results[0].keypoints is None:
            return {'keypoints': None, 'bbox': bbox, 'available': False}
        
        # Extract keypoints (first detection)
        keypoints_data = results[0].keypoints.data
        
        if len(keypoints_data) == 0:
            return {'keypoints': None, 'bbox': bbox, 'available': False}
        
        # Convert to numpy array (17, 3) - [x, y, confidence]
        keypoints = keypoints_data[0].cpu().numpy()
        
        # Convert from crop coordinates to full frame coordinates
        keypoints[:, 0] += x1  # Add bbox x offset
        keypoints[:, 1] += y1  # Add bbox y offset
        
        return {
            'keypoints': keypoints,
            'bbox': bbox,
            'available': True
        }
    
    def _detect_mediapipe_pose(self, person_crop: np.ndarray, bbox: Tuple[int, int, int, int]) -> Dict:
        """Detect pose using MediaPipe"""
        x1, y1, x2, y2 = bbox
        h, w = person_crop.shape[:2]
        
        # Convert BGR to RGB
        rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
        
        # Process
        results = self.model.process(rgb_crop)
        
        if not results.pose_landmarks:
            return {'keypoints': None, 'bbox': bbox, 'available': False}
        
        # Convert MediaPipe landmarks to COCO format
        # MediaPipe has 33 landmarks, we need to map to COCO 17
        mp_to_coco = {
            0: 0,   # nose
            2: 1,   # left_eye
            5: 2,   # right_eye
            7: 3,   # left_ear
            8: 4,   # right_ear
            11: 5,  # left_shoulder
            12: 6,  # right_shoulder
            13: 7,  # left_elbow
            14: 8,  # right_elbow
            15: 9,  # left_wrist
            16: 10, # right_wrist
            23: 11, # left_hip
            24: 12, # right_hip
            25: 13, # left_knee
            26: 14, # right_knee
            27: 15, # left_ankle
            28: 16  # right_ankle
        }
        
        keypoints = np.zeros((17, 3), dtype=np.float32)
        
        for mp_idx, coco_idx in mp_to_coco.items():
            landmark = results.pose_landmarks.landmark[mp_idx]
            # Convert normalized coordinates to pixel coordinates
            keypoints[coco_idx, 0] = landmark.x * w + x1
            keypoints[coco_idx, 1] = landmark.y * h + y1
            keypoints[coco_idx, 2] = landmark.visibility
        
        return {
            'keypoints': keypoints,
            'bbox': bbox,
            'available': True
        }
    
    def visualize_pose(self, frame: np.ndarray, pose: Dict, color=(0, 255, 0)) -> np.ndarray:
        """
        Draw pose keypoints and skeleton on frame
        
        Args:
            frame: Video frame
            pose: Pose dictionary from detect_poses()
            color: RGB color for visualization
        
        Returns:
            Frame with pose overlay
        """
        if not pose['available'] or pose['keypoints'] is None:
            return frame
        
        keypoints = pose['keypoints']
        
        # Draw keypoints
        for i, (x, y, conf) in enumerate(keypoints):
            if conf > self.confidence_threshold:
                cv2.circle(frame, (int(x), int(y)), 3, color, -1)
        
        # Draw skeleton connections
        skeleton = [
            (0, 1), (0, 2),  # nose to eyes
            (1, 3), (2, 4),  # eyes to ears
            (0, 5), (0, 6),  # nose to shoulders
            (5, 7), (7, 9),  # left arm
            (6, 8), (8, 10), # right arm
            (5, 11), (6, 12), # shoulders to hips
            (11, 12),        # hip connection
            (11, 13), (13, 15), # left leg
            (12, 14), (14, 16)  # right leg
        ]
        
        for i, j in skeleton:
            if (keypoints[i, 2] > self.confidence_threshold and 
                keypoints[j, 2] > self.confidence_threshold):
                pt1 = (int(keypoints[i, 0]), int(keypoints[i, 1]))
                pt2 = (int(keypoints[j, 0]), int(keypoints[j, 1]))
                cv2.line(frame, pt1, pt2, color, 2)
        
        return frame
    
    def is_available(self) -> bool:
        """Check if pose detection is available"""
        return self.available
