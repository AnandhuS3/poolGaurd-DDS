"""
Person Size Classification and Multi-Model Detection
Classifies persons as CHILD/ADULT based on size and uses ensemble detection
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class PersonSize(Enum):
    """Person size classification"""
    CHILD = "child"
    ADULT = "adult"
    UNKNOWN = "unknown"


@dataclass
class PersonMetrics:
    """Metrics for person size classification"""
    bbox_height: float
    bbox_width: float
    bbox_area: float
    aspect_ratio: float  # height / width
    relative_height: float  # height / frame_height
    relative_width: float  # width / frame_width
    shoulder_width: Optional[float] = None  # From pose keypoints
    head_size: Optional[float] = None  # From pose keypoints
    torso_length: Optional[float] = None  # From pose keypoints


class PersonSizeClassifier:
    """
    Classifies persons as CHILD or ADULT based on multiple metrics
    """
    
    def __init__(self, 
                 child_height_threshold: float = 0.35,
                 adult_height_threshold: float = 0.50,
                 child_area_threshold: float = 0.15,
                 adult_area_threshold: float = 0.25):
        """
        Initialize size classifier
        
        Args:
            child_height_threshold: Max relative height for child (0-1)
            adult_height_threshold: Min relative height for adult (0-1)
            child_area_threshold: Max relative area for child (0-1)
            adult_area_threshold: Min relative area for adult (0-1)
        """
        self.child_height_threshold = child_height_threshold
        self.adult_height_threshold = adult_height_threshold
        self.child_area_threshold = child_area_threshold
        self.adult_area_threshold = adult_area_threshold
    
    def extract_metrics(self, 
                       bbox: Tuple[int, int, int, int],
                       frame_height: int,
                       frame_width: int,
                       keypoints: Optional[np.ndarray] = None) -> PersonMetrics:
        """
        Extract size metrics from bounding box and optional pose keypoints
        
        Args:
            bbox: (x1, y1, x2, y2)
            frame_height: Video frame height
            frame_width: Video frame width
            keypoints: Optional pose keypoints (17, 3) - [x, y, confidence]
        
        Returns:
            PersonMetrics object
        """
        x1, y1, x2, y2 = bbox
        
        # Basic bbox metrics
        bbox_height = y2 - y1
        bbox_width = x2 - x1
        bbox_area = bbox_height * bbox_width
        aspect_ratio = bbox_height / max(bbox_width, 1)
        
        # Relative to frame
        relative_height = bbox_height / frame_height
        relative_width = bbox_width / frame_width
        
        # Pose-based metrics (if available)
        shoulder_width = None
        head_size = None
        torso_length = None
        
        if keypoints is not None and len(keypoints) == 17:
            # Shoulder width (left shoulder to right shoulder)
            left_shoulder = keypoints[5]  # Index 5
            right_shoulder = keypoints[6]  # Index 6
            
            if left_shoulder[2] > 0.3 and right_shoulder[2] > 0.3:
                shoulder_width = np.linalg.norm(
                    left_shoulder[:2] - right_shoulder[:2]
                )
            
            # Head size (nose to shoulder center)
            nose = keypoints[0]
            if nose[2] > 0.3 and shoulder_width is not None:
                shoulder_center = (left_shoulder[:2] + right_shoulder[:2]) / 2
                head_size = np.linalg.norm(nose[:2] - shoulder_center)
            
            # Torso length (shoulder center to hip center)
            left_hip = keypoints[11]
            right_hip = keypoints[12]
            
            if (left_shoulder[2] > 0.3 and right_shoulder[2] > 0.3 and
                left_hip[2] > 0.3 and right_hip[2] > 0.3):
                shoulder_center = (left_shoulder[:2] + right_shoulder[:2]) / 2
                hip_center = (left_hip[:2] + right_hip[:2]) / 2
                torso_length = np.linalg.norm(shoulder_center - hip_center)
        
        return PersonMetrics(
            bbox_height=bbox_height,
            bbox_width=bbox_width,
            bbox_area=bbox_area,
            aspect_ratio=aspect_ratio,
            relative_height=relative_height,
            relative_width=relative_width,
            shoulder_width=shoulder_width,
            head_size=head_size,
            torso_length=torso_length
        )
    
    def classify(self, metrics: PersonMetrics) -> PersonSize:
        """
        Classify person as CHILD or ADULT based on metrics
        
        Args:
            metrics: PersonMetrics object
        
        Returns:
            PersonSize enum
        """
        # Score-based classification
        child_score = 0
        adult_score = 0
        total_checks = 0
        
        # Check 1: Relative height
        if metrics.relative_height < self.child_height_threshold:
            child_score += 2
            total_checks += 2
        elif metrics.relative_height > self.adult_height_threshold:
            adult_score += 2
            total_checks += 2
        else:
            # In-between
            child_score += 1
            adult_score += 1
            total_checks += 2
        
        # Check 2: Relative area
        relative_area = metrics.bbox_area / (metrics.bbox_height * metrics.bbox_width + 1)
        if relative_area < self.child_area_threshold:
            child_score += 1
            total_checks += 1
        elif relative_area > self.adult_area_threshold:
            adult_score += 1
            total_checks += 1
        
        # Check 3: Aspect ratio (children tend to have different proportions)
        # Adults: 1.5-2.5, Children: 1.2-2.0
        if 1.2 <= metrics.aspect_ratio <= 2.0:
            child_score += 0.5
            total_checks += 1
        if 1.5 <= metrics.aspect_ratio <= 2.5:
            adult_score += 0.5
            total_checks += 1
        
        # Check 4: Pose-based metrics (if available)
        if metrics.shoulder_width is not None:
            # Normalize by bbox width
            shoulder_ratio = metrics.shoulder_width / metrics.bbox_width
            if shoulder_ratio < 0.4:
                child_score += 1
                total_checks += 1
            elif shoulder_ratio > 0.5:
                adult_score += 1
                total_checks += 1
        
        if metrics.head_size is not None and metrics.torso_length is not None:
            # Head-to-torso ratio (children have larger heads relative to body)
            head_torso_ratio = metrics.head_size / max(metrics.torso_length, 1)
            if head_torso_ratio > 0.5:  # Larger head
                child_score += 1
                total_checks += 1
            elif head_torso_ratio < 0.35:  # Smaller head
                adult_score += 1
                total_checks += 1
        
        # Make decision
        if total_checks == 0:
            return PersonSize.UNKNOWN
        
        child_confidence = child_score / total_checks
        adult_confidence = adult_score / total_checks
        
        if child_confidence > adult_confidence and child_confidence > 0.5:
            return PersonSize.CHILD
        elif adult_confidence > child_confidence and adult_confidence > 0.5:
            return PersonSize.ADULT
        else:
            return PersonSize.UNKNOWN
    
    def classify_from_bbox(self,
                          bbox: Tuple[int, int, int, int],
                          frame_height: int,
                          frame_width: int,
                          keypoints: Optional[np.ndarray] = None) -> Tuple[PersonSize, PersonMetrics]:
        """
        Convenience method to classify directly from bbox
        
        Returns:
            Tuple of (PersonSize, PersonMetrics)
        """
        metrics = self.extract_metrics(bbox, frame_height, frame_width, keypoints)
        size = self.classify(metrics)
        return size, metrics


class EnsembleDetector:
    """
    Ensemble detector using multiple YOLO models
    Combines detections from best.pt and best1.pt
    """
    
    def __init__(self, 
                 model_paths: List[str],
                 weights: Optional[List[float]] = None,
                 nms_threshold: float = 0.5,
                 confidence_threshold: float = 0.5):
        """
        Initialize ensemble detector
        
        Args:
            model_paths: List of paths to YOLO models
            weights: Optional weights for each model (default: equal weights)
            nms_threshold: NMS IoU threshold for combining detections
            confidence_threshold: Minimum confidence for detections
        """
        from ultralytics import YOLO
        
        self.models = [YOLO(path) for path in model_paths]
        self.weights = weights if weights else [1.0 / len(self.models)] * len(self.models)
        self.nms_threshold = nms_threshold
        self.confidence_threshold = confidence_threshold
        
        assert len(self.models) == len(self.weights), "Number of models must match number of weights"
        assert abs(sum(self.weights) - 1.0) < 0.01, "Weights must sum to 1.0"
    
    def detect(self, frame: np.ndarray, verbose: bool = False) -> List[Dict]:
        """
        Run ensemble detection on frame
        
        Args:
            frame: Input frame
            verbose: Print detection info
        
        Returns:
            List of detection dictionaries with weighted confidence scores
        """
        all_detections = []
        
        # Run each model
        for model, weight in zip(self.models, self.weights):
            results = model(frame, verbose=verbose)
            
            if len(results) > 0 and len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                    conf = float(box.conf[0]) * weight  # Apply model weight
                    cls = int(box.cls[0])
                    
                    all_detections.append({
                        'bbox': (x1, y1, x2, y2),
                        'confidence': conf,
                        'class': cls
                    })
        
        # Apply NMS to combine overlapping detections
        if len(all_detections) == 0:
            return []
        
        combined = self._weighted_nms(all_detections)
        
        # Filter by confidence threshold
        filtered = [d for d in combined if d['confidence'] >= self.confidence_threshold]
        
        return filtered
    
    def _weighted_nms(self, detections: List[Dict]) -> List[Dict]:
        """
        Weighted Non-Maximum Suppression
        Combines overlapping detections by averaging their boxes weighted by confidence
        """
        if len(detections) == 0:
            return []
        
        # Sort by confidence
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        keep = []
        
        while len(detections) > 0:
            # Take highest confidence detection
            best = detections[0]
            detections = detections[1:]
            
            # Find overlapping detections
            overlapping = [best]
            remaining = []
            
            for det in detections:
                iou = self._compute_iou(best['bbox'], det['bbox'])
                if iou > self.nms_threshold:
                    overlapping.append(det)
                else:
                    remaining.append(det)
            
            # Combine overlapping detections
            if len(overlapping) > 1:
                combined = self._combine_detections(overlapping)
                keep.append(combined)
            else:
                keep.append(best)
            
            detections = remaining
        
        return keep
    
    def _compute_iou(self, box1: Tuple, box2: Tuple) -> float:
        """Compute IoU between two boxes"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / max(union, 1)
    
    def _combine_detections(self, detections: List[Dict]) -> Dict:
        """Combine overlapping detections by weighted averaging"""
        total_conf = sum(d['confidence'] for d in detections)
        
        # Weighted average of bboxes
        x1 = sum(d['bbox'][0] * d['confidence'] for d in detections) / total_conf
        y1 = sum(d['bbox'][1] * d['confidence'] for d in detections) / total_conf
        x2 = sum(d['bbox'][2] * d['confidence'] for d in detections) / total_conf
        y2 = sum(d['bbox'][3] * d['confidence'] for d in detections) / total_conf
        
        return {
            'bbox': (int(x1), int(y1), int(x2), int(y2)),
            'confidence': total_conf / len(detections),  # Average confidence
            'class': detections[0]['class']  # Use class from best detection
        }


# Example usage
if __name__ == "__main__":
    # Test size classifier
    classifier = PersonSizeClassifier()
    
    # Test case 1: Small child
    child_bbox = (100, 200, 200, 400)  # 100x200 pixels
    frame_height, frame_width = 1080, 1920
    
    size, metrics = classifier.classify_from_bbox(child_bbox, frame_height, frame_width)
    print(f"Test 1 - Child bbox: {size.value}")
    print(f"  Metrics: height={metrics.relative_height:.3f}, area={metrics.bbox_area}")
    
    # Test case 2: Adult
    adult_bbox = (100, 100, 300, 700)  # 200x600 pixels
    size, metrics = classifier.classify_from_bbox(adult_bbox, frame_height, frame_width)
    print(f"\nTest 2 - Adult bbox: {size.value}")
    print(f"  Metrics: height={metrics.relative_height:.3f}, area={metrics.bbox_area}")
    
    print("\n✅ Size classifier ready!")
    print("✅ Ensemble detector ready!")
    print("\nNext: Integrate into video processing pipeline")
