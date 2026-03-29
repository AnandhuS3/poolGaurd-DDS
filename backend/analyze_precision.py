import cv2
import numpy as np
import time
import sys
import os
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# Add the parent directory to Python path so we can import core modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import *

try:
    from core.behavior.inference import RiskInferenceEngine
    from core.pose_estimation.pose_detector import PoseDetector
    LSTM_AVAILABLE = True
except ImportError:
    print("Warning: LSTM / Behavior modules could not be imported. We will only test standard YOLO detection.")
    LSTM_AVAILABLE = False
    
def main():
    video_path = "../assets/uploads/demo_974225.mp4"
    if not os.path.exists(video_path):
        print(f"Error: Video not found at {video_path}")
        return

    print("Initializing YOLO Models (Ensemble)...")
    # TWEAKED SETTINGS for balancing baby detection vs rigid objects vs speed
    CUSTOM_CONFIDENCE = 0.25  # Balance: Catch the baby, but don't overwhelm the system
    CUSTOM_IMG_SIZE = 1088    # High resolution
    FRAME_SKIP = 3            # Process every 3rd frame (10 FPS) for massive speed boost!
    
    # Tracker Tuning for better persistency
    CUSTOM_MAX_AGE = 60
    CUSTOM_N_INIT = 3
    
    config.CONFIDENCE_THRESHOLD = CUSTOM_CONFIDENCE
    config.YOLO_IMG_SIZE = CUSTOM_IMG_SIZE

    # Initialize...
    from ultralytics import YOLO
    model = YOLO(MODEL_PATH)
    if hasattr(model, 'device'):
        model.to('cuda' if __import__('torch').cuda.is_available() else 'cpu')
        
    model_secondary = None
    if os.path.exists(MODEL_PATH_SECONDARY):
        model_secondary = YOLO(MODEL_PATH_SECONDARY)
        if hasattr(model_secondary, 'device'):
            model_secondary.to('cuda' if __import__('torch').cuda.is_available() else 'cpu')
    
    from backend.core.state_manager import TrackerManager
    tracker = TrackerManager(max_age=CUSTOM_MAX_AGE, n_init=CUSTOM_N_INIT)
    # slightly loose distance to keep tracks matching 
    if hasattr(tracker.tracker, 'metric') and hasattr(tracker.tracker.metric, 'matching_threshold'):
          tracker.tracker.metric.matching_threshold = 0.4
          
    from backend.core.pose_estimation.pose_detector import PoseDetector
    from backend.core.behavior_classification.lstm_engine import LSTMEngine
    secondary_pose_detector = PoseDetector(model_type="yolov8-pose")
    lstm_engine = LSTMEngine()
    
    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video Loaded: {fps} FPS | {total_frames} Frames")
    print("Analysis started. Press 'q' to quit early.")

    frame_idx = 0
    processed_frames = 0
    total_detections_count = 0
    sum_confidence = 0.0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_idx += 1
        
        if frame_idx % FRAME_SKIP != 0:
            continue
            
        processed_frames += 1
        
        # Unified window
        display_frame = frame.copy()

        # -----------------------------------------------------------------
        # 1. Standard Object Detection (Ensemble)
        # -----------------------------------------------------------------
        results1 = model(frame, conf=CUSTOM_CONFIDENCE, imgsz=CUSTOM_IMG_SIZE, verbose=False)
        
        raw_detections = []
        for result in results1:
            for box in result.boxes:
                cls = int(box.cls[0])
                # Only accept PERSON (0) or DROWNING (1) class if the model supports multiple
                if cls not in [PERSON_CLASS_ID, DROWNING_CLASS_ID, 0, 1]:
                    continue
                    
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                raw_detections.append(([x1, y1, x2 - x1, y2 - y1], conf, cls))
                
        # Run secondary model if available
        if model_secondary:
            results2 = model_secondary(frame, conf=CUSTOM_CONFIDENCE, imgsz=CUSTOM_IMG_SIZE, verbose=False)
            for result in results2:
                for box in result.boxes:
                    cls = int(box.cls[0])
                    if cls not in [PERSON_CLASS_ID, DROWNING_CLASS_ID, 0, 1]:
                        continue
                        
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    # Boost ensemble confidence slightly
                    raw_detections.append(([x1, y1, x2 - x1, y2 - y1], min(conf * 1.05, 1.0), cls))
                    
        # Apply NMS to remove duplicate bounding boxes strictly
        detections = []
        if len(raw_detections) > 0:
            boxes = [d[0] for d in raw_detections]
            scores = [d[1] for d in raw_detections]
            
            indices = cv2.dnn.NMSBoxes(
                bboxes=boxes, 
                scores=scores, 
                score_threshold=CUSTOM_CONFIDENCE, 
                nms_threshold=0.5 # Stricter duplicate overlapping setting
            )
            
            if len(indices) > 0:
                if isinstance(indices, np.ndarray):
                    indices = indices.flatten().tolist()
                elif isinstance(indices, (list, tuple)) and len(indices) > 0 and isinstance(indices[0], (list, np.ndarray)):
                     indices = [i[0] for i in indices]
                     
                for i in indices:
                    detections.append(raw_detections[i])
                    total_detections_count += 1
                    sum_confidence += raw_detections[i][1]

        # DeepSORT update
        tracks = tracker.update_tracks(detections, frame=frame)
        
        # -----------------------------------------------------------------
        # 2. Pose & LSTM Behavior on Tracked People
        # -----------------------------------------------------------------
        lstm_results = {}
        if LSTM_AVAILABLE and secondary_pose_detector.is_available() and lstm_engine.is_available():
            # Apply Pose analysis every N frames (we skip some inference for speed but maintain state)
            bboxes_for_lstm = []
            track_ids_for_lstm = []
            
            for track in tracks:
                if not track.is_confirmed():
                    continue
                bboxes_for_lstm.append(tuple(map(int, track.to_ltrb())))
                track_ids_for_lstm.append(track.track_id)
            
            if len(bboxes_for_lstm) > 0:
                poses = secondary_pose_detector.detect_poses(frame, bboxes_for_lstm)
                
                for track_id, pose, bbox in zip(track_ids_for_lstm, poses, bboxes_for_lstm):
                    if pose and 'keypoints' in pose and pose['keypoints'] is not None:
                        keypoints = pose['keypoints']
                        
                        # STRICT VALIDATION: Ensure this is a real person by checking if they have at least 3 confident keypoints
                        valid_kps = sum(1 for kp in keypoints if kp[2] > 0.5)
                        if valid_kps < 3:
                            continue # Ignore rigid objects! Don't pass to LSTM.

                        # Draw keypoints directly on unified display
                        for kp in keypoints:
                            x, y, kp_conf = kp
                            if kp_conf > 0.5:
                                cv2.circle(display_frame, (int(x), int(y)), 4, (0, 255, 255), -1)

                        # Process behavioral risk
                        risk_result = lstm_engine.process_track(
                            track_id=track_id,
                            keypoints=keypoints,
                            bbox=bbox,
                            frame_height=frame.shape[0],
                            frame_number=frame_idx
                        )
                        lstm_results[track_id] = risk_result
        
        # Draw unified tracking boxes & behavioral state
        global_system_state = "SAFE"
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            track_id = track.track_id
            ltrb = track.to_ltrb()
            x1, y1, x2, y2 = map(int, ltrb)
            
            # If LSTM evaluated this track, override box color
            if track_id in lstm_results:
                risk_state = lstm_results[track_id]['risk_state']
                risk_conf = lstm_results[track_id]['confidence']
                
                # Upgrade global system state if necessary
                if risk_state == "DANGER":
                    global_system_state = "DANGER"
                elif risk_state == "WARNING" and global_system_state != "DANGER":
                    global_system_state = "WARNING"

                color = (0, 0, 255) if risk_state == "DANGER" else (
                    (0, 165, 255) if risk_state == "WARNING" else (0, 255, 0)
                )
                label = f"ID:{track_id} {risk_state}({risk_conf:.2f})"
                
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(display_frame, label, (x1, max(15, y1 - 10)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            else:
                # Ghost objects (Light, Chair, etc that YOLO flagged but Pose rejected)
                # We skip drawing huge shapes for these to keep the screen clean. 
                # Draw a tiny gray dot/box just to show tracking
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (100, 100, 100), 1)

        # Draw Global System State
        state_color = (0, 0, 255) if global_system_state == "DANGER" else (
            (0, 165, 255) if global_system_state == "WARNING" else (0, 255, 0)
        )
        cv2.putText(display_frame, f"SYSTEM STATE: {global_system_state}", (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, state_color, 4)

        # Trigger Audible Alarm
        if global_system_state == "DANGER":
            cv2.putText(display_frame, "!!! ALARM TRIGGERED !!!", (20, 100), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            # Use threading so the beep doesn't freeze the video playback loop
            import threading, winsound
            threading.Thread(target=lambda: winsound.Beep(1500, 300), daemon=True).start()

        # Display Windows
        # Resize display slightly to ensure they fit on screen comfortably
        display_scale = 0.7
        combined_display = cv2.resize(display_frame, (0,0), fx=display_scale, fy=display_scale)
        
        cv2.imshow("PoolGuard: Unified Detection & Behavior", combined_display)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    end_time = time.time()
    elapsed = end_time - start_time
    avg_conf = sum_confidence / total_detections_count if total_detections_count > 0 else 0
    actual_fps = frame_idx / elapsed if elapsed > 0 else 0

    print("==================================================")
    print("                ANALYSIS RESULTS                  ")
    print("==================================================")
    print(f"Total Frames Processed : {frame_idx}")
    print(f"Total Detections       : {total_detections_count}")
    print(f"Avg Detection Conf     : {avg_conf:.4f}")
    print(f"Processing Speed       : {actual_fps:.2f} FPS")
    print("==================================================")

if __name__ == "__main__":
    main()
