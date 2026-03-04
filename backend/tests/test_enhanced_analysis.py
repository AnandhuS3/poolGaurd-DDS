"""
Enhanced Video Analysis Test - Full Pose-Driven + LSTM + Behavior Classification
Includes proper tracking, pose visualization, and behavior analysis
"""

import cv2
import numpy as np
import sys
import time
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, '.')

from core.pose_estimation.pose_detector import PoseDetector
from core.pose_estimation.keypoint_analyzer import KeypointAnalyzer
from core.behavior_classification.temporal_buffer import TemporalBuffer
from core.behavior_classification.behavior_classifier import BehaviorClassifier
from core.behavior_classification.state_machine import StateMachine
from core.behavior.inference import RiskInferenceEngine
from core.behavior.temporal_model import create_dummy_model
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# Configuration
VIDEO_PATH = "test_video.mp4"
OUTPUT_PATH = "output_enhanced_analysis.mp4"
DISPLAY_WINDOW = False  # Headless by default (no libGL needed); pass --display to enable locally
SAVE_OUTPUT = True

# Model paths
DETECTION_MODEL = "weights/best.pt"
POSE_MODEL = "weights/behavior/yolov8n-pose.pt"
LSTM_MODEL = "weights/behavior/drowning_lstm.pt"

# Processing settings
FRAME_SKIP = 2  # Process every 2nd frame for LSTM
RESIZE_FOR_POSE = 512
CONFIDENCE_THRESHOLD = 0.5

# Colors
COLOR_SAFE = (0, 255, 0)
COLOR_ATTENTION = (0, 255, 255)  # Yellow
COLOR_WARNING = (0, 165, 255)
COLOR_DANGER = (0, 0, 255)
COLOR_TEXT = (255, 255, 255)
COLOR_BG = (0, 0, 0)
COLOR_POSE = (255, 0, 255)  # Magenta for pose keypoints


def draw_text_with_background(frame, text, position, font_scale=0.6, thickness=2, 
                               text_color=COLOR_TEXT, bg_color=COLOR_BG):
    """Draw text with background for better visibility"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    x, y = position
    cv2.rectangle(frame, (x, y - text_height - 5), (x + text_width + 5, y + 5), bg_color, -1)
    cv2.putText(frame, text, (x, y), font, font_scale, text_color, thickness)
    return text_height + 10


def draw_pose_skeleton(frame, keypoints, confidence_threshold=0.3):
    """Draw pose keypoints and skeleton"""
    if keypoints is None or len(keypoints) == 0:
        return
    
    # Draw keypoints
    for i, (x, y, conf) in enumerate(keypoints):
        if conf > confidence_threshold:
            cv2.circle(frame, (int(x), int(y)), 4, COLOR_POSE, -1)
            cv2.circle(frame, (int(x), int(y)), 5, COLOR_TEXT, 1)
    
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
        if i < len(keypoints) and j < len(keypoints):
            if (keypoints[i, 2] > confidence_threshold and 
                keypoints[j, 2] > confidence_threshold):
                pt1 = (int(keypoints[i, 0]), int(keypoints[i, 1]))
                pt2 = (int(keypoints[j, 0]), int(keypoints[j, 1]))
                cv2.line(frame, pt1, pt2, COLOR_POSE, 2)


def draw_risk_bar(frame, risk_scores, position, width=200, height=30):
    """Draw risk probability bar chart"""
    x, y = position
    labels = ['SAFE', 'WARN', 'DNGR']
    colors = [COLOR_SAFE, COLOR_WARNING, COLOR_DANGER]
    
    cv2.rectangle(frame, (x, y), (x + width, y + height), COLOR_BG, -1)
    
    bar_width = width // 3
    for i, (score, label, color) in enumerate(zip(risk_scores, labels, colors)):
        bar_x = x + i * bar_width
        bar_height = int(score * height)
        bar_y = y + height - bar_height
        
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width - 2, y + height), color, -1)
        
        cv2.putText(frame, label, (bar_x + 5, y + height + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        cv2.putText(frame, f"{score:.2f}", (bar_x + 5, y + height + 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_TEXT, 1)


def analyze_video(video_path):
    """Main video analysis function with full pipeline"""
    
    print("=" * 70)
    print("Enhanced Video Analysis - Full Pipeline")
    print("Pose-Driven + Behavior Classification + LSTM Risk Inference")
    print("=" * 70)
    
    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        return
    
    # Initialize models
    print("\n1. Initializing models...")
    
    # Person detection
    print("   Loading person detection model...")
    try:
        detection_model = YOLO(DETECTION_MODEL)
        print(f"   ✅ Detection model loaded")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return
    
    # DeepSORT tracker
    print("   Initializing DeepSORT tracker...")
    try:
        tracker = DeepSort(max_age=30, n_init=3, nms_max_overlap=1.0, 
                          max_cosine_distance=0.3, nn_budget=None)
        print(f"   ✅ Tracker initialized")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return
    
    # Pose estimation
    print("   Loading pose estimation model...")
    try:
        pose_detector = PoseDetector(
            model_type="yolov8-pose",
            model_path=POSE_MODEL,
            confidence_threshold=0.3,
            device='cpu'
        )
        print(f"   ✅ Pose detector loaded")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return
    
    # Behavior classification components
    print("   Initializing behavior classification...")
    try:
        keypoint_analyzer = KeypointAnalyzer()
        temporal_buffer = TemporalBuffer(window_size=90)
        behavior_classifier = BehaviorClassifier()
        state_machine = StateMachine()
        print(f"   ✅ Behavior classification ready")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return
    
    # LSTM risk inference
    print("   Loading LSTM risk inference...")
    try:
        lstm_path = Path(LSTM_MODEL)
        if not lstm_path.exists():
            print(f"   Creating dummy LSTM model...")
            lstm_path.parent.mkdir(parents=True, exist_ok=True)
            create_dummy_model(lstm_path)
        
        lstm_engine = RiskInferenceEngine(
            model_path=str(lstm_path),
            buffer_size=90,
            min_frames=30,
            device='cpu'
        )
        print(f"   ✅ LSTM engine loaded")
        print(f"   ⚠️  Using dummy model - predictions will be mostly SAFE")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return
    
    # Open video
    print(f"\n2. Opening video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"   ❌ Failed to open video")
        return
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"   ✅ Video opened successfully")
    print(f"   - Resolution: {width}x{height}")
    print(f"   - FPS: {fps}")
    print(f"   - Total frames: {total_frames}")
    print(f"   - Duration: {total_frames/fps:.1f} seconds")
    
    # Setup output video
    out = None
    if SAVE_OUTPUT:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))
        print(f"\n3. Output will be saved to: {OUTPUT_PATH}")
    
    # Processing loop
    print(f"\n4. Processing video...")
    print(f"   Press 'q' to quit, 'p' to pause/resume")
    
    frame_count = 0
    paused = False
    start_time = time.time()
    
    # Track data
    person_data = defaultdict(lambda: {
        'state': 'SAFE',
        'behavior': 'unknown',
        'frames_tracked': 0,
        'pose_history': []
    })
    
    # Statistics
    stats = {
        'total_detections': 0,
        'pose_detections': 0,
        'lstm_inferences': 0,
        'behaviors': defaultdict(int),
        'states': defaultdict(int)
    }
    
    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            display_frame = frame.copy()
            
            # Run person detection
            results = detection_model(frame, verbose=False, conf=CONFIDENCE_THRESHOLD)
            
            # Prepare detections for DeepSORT
            detections = []
            if len(results) > 0 and len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    
                    # DeepSORT format: ([x1, y1, w, h], confidence, class)
                    detections.append(([x1, y1, x2-x1, y2-y1], conf, cls))
                    stats['total_detections'] += 1
            
            # Update tracker
            tracks = tracker.update_tracks(detections, frame=frame)
            
            # Process each track
            for track in tracks:
                if not track.is_confirmed():
                    continue
                
                track_id = track.track_id
                ltrb = track.to_ltrb()
                x1, y1, x2, y2 = map(int, ltrb)
                
                person_data[track_id]['frames_tracked'] += 1
                
                # Run pose detection
                pose_result = None
                if frame_count % FRAME_SKIP == 0:
                    # Resize for faster inference
                    scale = RESIZE_FOR_POSE / max(width, height)
                    resized_width = int(width * scale)
                    resized_height = int(height * scale)
                    resized_frame = cv2.resize(frame, (resized_width, resized_height))
                    
                    # Scale bbox
                    scaled_bbox = (
                        int(x1 * scale), int(y1 * scale),
                        int(x2 * scale), int(y2 * scale)
                    )
                    
                    # Detect pose
                    poses = pose_detector.detect_poses(resized_frame, [scaled_bbox])
                    
                    if len(poses) > 0 and poses[0]['available']:
                        pose_result = poses[0]
                        stats['pose_detections'] += 1
                        
                        # Scale keypoints back to original size
                        keypoints = pose_result['keypoints'].copy()
                        keypoints[:, 0] /= scale
                        keypoints[:, 1] /= scale
                        
                        # Analyze pose features
                        pose_dict = {
                            'available': True,
                            'keypoints': keypoints,
                            'bbox': (x1, y1, x2, y2)
                        }
                        pose_features = keypoint_analyzer.analyze(
                            pose_dict,
                            height, width, track_id
                        )
                        
                        if pose_features:
                            # Add to temporal buffer
                            temporal_buffer.add_features(track_id, pose_features)
                            
                            # Get temporal statistics
                            temporal_stats = temporal_buffer.get_statistics(track_id)
                            
                            # Classify behavior
                            behavior = behavior_classifier.classify(pose_features, temporal_stats)
                            person_data[track_id]['behavior'] = behavior.value
                            stats['behaviors'][behavior.value] += 1
                            
                            # Update state machine
                            state = state_machine.update(track_id, behavior, frame_count)
                            person_data[track_id]['state'] = state.value
                            stats['states'][state.value] += 1
                            
                            # Run LSTM inference
                            risk_result = lstm_engine.process_track(
                                track_id=track_id,
                                keypoints=pose_result['keypoints'],
                                bbox=scaled_bbox,
                                frame_height=resized_height,
                                frame_number=frame_count
                            )
                            
                            if risk_result['inference_ready']:
                                stats['lstm_inferences'] += 1
                                person_data[track_id]['lstm_risk'] = risk_result['risk_state']
                                person_data[track_id]['lstm_scores'] = risk_result['risk_scores']
                                person_data[track_id]['lstm_confidence'] = risk_result['confidence']
                            
                            # Store keypoints for visualization
                            person_data[track_id]['keypoints'] = keypoints
                
                # Determine color based on state
                state = person_data[track_id]['state']
                if state == 'SAFE':
                    color = COLOR_SAFE
                elif state == 'ATTENTION':
                    color = COLOR_ATTENTION
                elif state == 'WARNING':
                    color = COLOR_WARNING
                else:
                    color = COLOR_DANGER
                
                # Draw bounding box
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 3)
                
                # Draw pose skeleton
                if 'keypoints' in person_data[track_id]:
                    draw_pose_skeleton(display_frame, person_data[track_id]['keypoints'])
                
                # Draw person info
                y_offset = y1 - 10
                label = f"ID:{track_id} {state}"
                y_offset -= draw_text_with_background(
                    display_frame, label, (x1, y_offset), 
                    font_scale=0.6, text_color=color
                )
                
                # Draw behavior
                behavior = person_data[track_id].get('behavior', 'unknown')
                if behavior != 'unknown':
                    behavior_label = f"Behavior: {behavior}"
                    y_offset -= draw_text_with_background(
                        display_frame, behavior_label, (x1, y_offset),
                        font_scale=0.5, text_color=color
                    )
                
                # Draw LSTM risk
                if 'lstm_risk' in person_data[track_id]:
                    lstm_label = f"LSTM: {person_data[track_id]['lstm_risk']}"
                    y_offset -= draw_text_with_background(
                        display_frame, lstm_label, (x1, y_offset),
                        font_scale=0.5
                    )
                    
                    # Draw risk bars
                    if 'lstm_scores' in person_data[track_id]:
                        draw_risk_bar(
                            display_frame,
                            person_data[track_id]['lstm_scores'],
                            (x1, y2 + 10),
                            width=min(200, x2 - x1)
                        )
                
                # Draw tracking info
                frames_label = f"Tracked: {person_data[track_id]['frames_tracked']} frames"
                draw_text_with_background(
                    display_frame, frames_label, (x1, y_offset),
                    font_scale=0.4
                )
            
            # Draw frame info
            info_y = 30
            draw_text_with_background(
                display_frame, f"Frame: {frame_count}/{total_frames}",
                (10, info_y), font_scale=0.7
            )
            info_y += 30
            
            elapsed = time.time() - start_time
            current_fps = frame_count / elapsed if elapsed > 0 else 0
            draw_text_with_background(
                display_frame, f"FPS: {current_fps:.1f}",
                (10, info_y), font_scale=0.7
            )
            info_y += 30
            
            draw_text_with_background(
                display_frame, f"Detections: {stats['total_detections']}",
                (10, info_y), font_scale=0.6
            )
            info_y += 25
            
            draw_text_with_background(
                display_frame, f"Poses: {stats['pose_detections']}",
                (10, info_y), font_scale=0.6
            )
            info_y += 25
            
            draw_text_with_background(
                display_frame, f"LSTM: {stats['lstm_inferences']}",
                (10, info_y), font_scale=0.6
            )
            info_y += 25
            
            draw_text_with_background(
                display_frame, f"Tracks: {len([t for t in tracks if t.is_confirmed()])}",
                (10, info_y), font_scale=0.6
            )
            
            # Draw legend
            legend_x = width - 180
            legend_y = 30
            cv2.rectangle(display_frame, (legend_x - 5, legend_y - 25), 
                         (width - 5, legend_y + 95), COLOR_BG, -1)
            
            cv2.putText(display_frame, "STATES:", (legend_x, legend_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)
            legend_y += 25
            
            for state_name, state_color in [('SAFE', COLOR_SAFE), ('ATTENTION', COLOR_ATTENTION),
                                            ('WARNING', COLOR_WARNING), ('DANGER', COLOR_DANGER)]:
                cv2.rectangle(display_frame, (legend_x, legend_y - 10), 
                             (legend_x + 15, legend_y), state_color, -1)
                cv2.putText(display_frame, state_name, (legend_x + 20, legend_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_TEXT, 1)
                legend_y += 20
            
            # Save frame
            if SAVE_OUTPUT and out is not None:
                out.write(display_frame)
            
            # Display frame
            if DISPLAY_WINDOW:
                cv2.imshow('Enhanced Analysis - Pose + Behavior + LSTM', display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n   User requested quit")
                    break
                elif key == ord('p'):
                    paused = not paused
                    print(f"\n   {'Paused' if paused else 'Resumed'}")
            
            # Progress update
            if frame_count % 30 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"   Progress: {progress:.1f}% ({frame_count}/{total_frames}) - FPS: {current_fps:.1f}")
        
        else:
            if DISPLAY_WINDOW:
                key = cv2.waitKey(100) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('p'):
                    paused = False
                    print(f"\n   Resumed")
    
    # Cleanup
    cap.release()
    if out is not None:
        out.release()
    if DISPLAY_WINDOW:
        cv2.destroyAllWindows()
    
    # Final statistics
    print("\n" + "=" * 70)
    print("Analysis Complete!")
    print("=" * 70)
    print(f"\nProcessing Statistics:")
    print(f"  Total frames processed: {frame_count}")
    print(f"  Total person detections: {stats['total_detections']}")
    print(f"  Successful pose detections: {stats['pose_detections']}")
    print(f"  LSTM inferences: {stats['lstm_inferences']}")
    print(f"  Unique tracks: {len(person_data)}")
    
    print(f"\nBehavior Distribution:")
    for behavior, count in sorted(stats['behaviors'].items()):
        print(f"  {behavior}: {count}")
    
    print(f"\nState Distribution:")
    for state, count in sorted(stats['states'].items()):
        print(f"  {state}: {count}")
    
    print(f"\nPerformance:")
    elapsed = time.time() - start_time
    print(f"  Total time: {elapsed:.1f} seconds")
    print(f"  Average FPS: {frame_count / elapsed:.1f}")
    
    if SAVE_OUTPUT:
        print(f"\n✅ Output saved to: {OUTPUT_PATH}")
    
    print("\n⚠️  NOTE: LSTM predictions are from dummy model (mostly SAFE)")
    print("   Train LSTM on real drowning data for accurate risk assessment")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Video Analysis')
    parser.add_argument('--video', type=str, default=VIDEO_PATH,
                       help='Path to input video file')
    parser.add_argument('--output', type=str, default=OUTPUT_PATH,
                       help='Path to output video file')
    parser.add_argument('--display', action='store_true',
                       help='Enable live display window (requires a local GUI / X server)')
    parser.add_argument('--no-save', action='store_true',
                       help='Do not save output video')
    
    args = parser.parse_args()
    
    VIDEO_PATH = args.video
    OUTPUT_PATH = args.output
    DISPLAY_WINDOW = args.display
    SAVE_OUTPUT = not args.no_save
    
    analyze_video(VIDEO_PATH)
