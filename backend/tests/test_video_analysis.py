"""
Video Analysis Test - Pose-Driven + LSTM Risk Inference
Analyzes a video file and displays real-time pose detection and LSTM risk scores
"""

import cv2
import numpy as np
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, '.')

from core.pose_estimation.pose_detector import PoseDetector
from core.behavior.inference import RiskInferenceEngine
from core.behavior.temporal_model import create_dummy_model
from ultralytics import YOLO

# Configuration
VIDEO_PATH = "test_video.mp4"  # Change this to your video path
OUTPUT_PATH = "output_analysis.mp4"  # Output video with annotations
DISPLAY_WINDOW = False  # Headless by default (no libGL needed); pass --display to enable locally
SAVE_OUTPUT = True  # Save annotated video

# Model paths
DETECTION_MODEL = "weights/best.pt"  # Person detection
POSE_MODEL = "weights/behavior/yolov8n-pose.pt"  # Pose estimation
LSTM_MODEL = "weights/behavior/drowning_lstm.pt"  # LSTM classifier

# Processing settings
FRAME_SKIP = 2  # Process every 2nd frame for LSTM
RESIZE_FOR_POSE = 512  # Resize for faster pose inference
CONFIDENCE_THRESHOLD = 0.5

# Colors
COLOR_SAFE = (0, 255, 0)      # Green
COLOR_WARNING = (0, 165, 255)  # Orange
COLOR_DANGER = (0, 0, 255)     # Red
COLOR_TEXT = (255, 255, 255)   # White
COLOR_BG = (0, 0, 0)           # Black


def draw_text_with_background(frame, text, position, font_scale=0.6, thickness=2, 
                               text_color=COLOR_TEXT, bg_color=COLOR_BG):
    """Draw text with background for better visibility"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    x, y = position
    # Draw background rectangle
    cv2.rectangle(frame, (x, y - text_height - 5), (x + text_width + 5, y + 5), bg_color, -1)
    # Draw text
    cv2.putText(frame, text, (x, y), font, font_scale, text_color, thickness)
    return text_height + 10


def draw_risk_bar(frame, risk_scores, position, width=200, height=30):
    """Draw risk probability bar chart"""
    x, y = position
    labels = ['SAFE', 'WARN', 'DNGR']
    colors = [COLOR_SAFE, COLOR_WARNING, COLOR_DANGER]
    
    # Draw background
    cv2.rectangle(frame, (x, y), (x + width, y + height), COLOR_BG, -1)
    
    # Draw bars
    bar_width = width // 3
    for i, (score, label, color) in enumerate(zip(risk_scores, labels, colors)):
        bar_x = x + i * bar_width
        bar_height = int(score * height)
        bar_y = y + height - bar_height
        
        # Draw bar
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width - 2, y + height), color, -1)
        
        # Draw label
        label_text = f"{label}\n{score:.2f}"
        cv2.putText(frame, label, (bar_x + 5, y + height + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        cv2.putText(frame, f"{score:.2f}", (bar_x + 5, y + height + 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_TEXT, 1)


def analyze_video(video_path):
    """Main video analysis function"""
    
    print("=" * 70)
    print("Video Analysis - Pose-Driven + LSTM Risk Inference")
    print("=" * 70)
    
    # Check video exists
    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        print(f"Please provide a valid video path")
        return
    
    # Initialize models
    print("\n1. Initializing models...")
    
    # Person detection model
    print("   Loading person detection model...")
    try:
        detection_model = YOLO(DETECTION_MODEL)
        print(f"   ✅ Detection model loaded: {DETECTION_MODEL}")
    except Exception as e:
        print(f"   ❌ Failed to load detection model: {e}")
        return
    
    # Pose estimation model
    print("   Loading pose estimation model...")
    try:
        pose_detector = PoseDetector(
            model_type="yolov8-pose",
            model_path=POSE_MODEL,
            confidence_threshold=0.3,
            device='cpu'
        )
        print(f"   ✅ Pose detector loaded: {POSE_MODEL}")
    except Exception as e:
        print(f"   ❌ Failed to load pose detector: {e}")
        return
    
    # LSTM risk inference
    print("   Loading LSTM risk inference...")
    try:
        # Create dummy model if not exists
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
        print(f"   ✅ LSTM engine loaded: {LSTM_MODEL}")
        print(f"   ⚠️  Using dummy model - replace with trained model for production")
    except Exception as e:
        print(f"   ❌ Failed to load LSTM engine: {e}")
        return
    
    # Open video
    print(f"\n2. Opening video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"   ❌ Failed to open video")
        return
    
    # Get video properties
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
    
    # Statistics
    stats = {
        'total_detections': 0,
        'pose_detections': 0,
        'lstm_inferences': 0,
        'safe_frames': 0,
        'warning_frames': 0,
        'danger_frames': 0
    }
    
    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Create display frame
            display_frame = frame.copy()
            
            # Run person detection
            results = detection_model(frame, verbose=False, conf=CONFIDENCE_THRESHOLD)
            
            if len(results) > 0 and len(results[0].boxes) > 0:
                boxes = results[0].boxes
                
                # Extract bounding boxes
                bboxes = []
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                    bboxes.append((x1, y1, x2, y2))
                    stats['total_detections'] += 1
                
                # Run pose detection
                if frame_count % FRAME_SKIP == 0:
                    # Resize for faster pose inference
                    scale = RESIZE_FOR_POSE / max(width, height)
                    resized_width = int(width * scale)
                    resized_height = int(height * scale)
                    resized_frame = cv2.resize(frame, (resized_width, resized_height))
                    
                    # Scale bboxes
                    scaled_bboxes = []
                    for (x1, y1, x2, y2) in bboxes:
                        scaled_bboxes.append((
                            int(x1 * scale), int(y1 * scale),
                            int(x2 * scale), int(y2 * scale)
                        ))
                    
                    # Detect poses
                    poses = pose_detector.detect_poses(resized_frame, scaled_bboxes)
                    
                    # Process each person
                    for idx, (bbox, pose) in enumerate(zip(bboxes, poses)):
                        x1, y1, x2, y2 = bbox
                        track_id = idx + 1  # Simple track ID
                        
                        if pose['available'] and pose['keypoints'] is not None:
                            stats['pose_detections'] += 1
                            
                            # Run LSTM inference
                            scaled_bbox = scaled_bboxes[idx]
                            risk_result = lstm_engine.process_track(
                                track_id=track_id,
                                keypoints=pose['keypoints'],
                                bbox=scaled_bbox,
                                frame_height=resized_height,
                                frame_number=frame_count
                            )
                            
                            if risk_result['inference_ready']:
                                stats['lstm_inferences'] += 1
                            
                            # Determine color based on risk
                            risk_state = risk_result['risk_state']
                            if risk_state == 'SAFE':
                                color = COLOR_SAFE
                                stats['safe_frames'] += 1
                            elif risk_state == 'WARNING':
                                color = COLOR_WARNING
                                stats['warning_frames'] += 1
                            else:
                                color = COLOR_DANGER
                                stats['danger_frames'] += 1
                            
                            # Draw bounding box
                            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 3)
                            
                            # Draw person info
                            y_offset = y1 - 10
                            label = f"Person #{track_id}"
                            y_offset -= draw_text_with_background(
                                display_frame, label, (x1, y_offset), 
                                font_scale=0.6, text_color=color
                            )
                            
                            # Draw risk state
                            risk_label = f"Risk: {risk_state}"
                            y_offset -= draw_text_with_background(
                                display_frame, risk_label, (x1, y_offset),
                                font_scale=0.5, text_color=color
                            )
                            
                            # Draw confidence
                            conf_label = f"Conf: {risk_result['confidence']:.2f}"
                            y_offset -= draw_text_with_background(
                                display_frame, conf_label, (x1, y_offset),
                                font_scale=0.5
                            )
                            
                            # Draw buffer status
                            buffer_label = f"Buffer: {risk_result['buffer_size']}/90"
                            y_offset -= draw_text_with_background(
                                display_frame, buffer_label, (x1, y_offset),
                                font_scale=0.4
                            )
                            
                            # Draw risk probability bars
                            if risk_result['inference_ready']:
                                draw_risk_bar(
                                    display_frame,
                                    risk_result['risk_scores'],
                                    (x1, y2 + 10),
                                    width=min(200, x2 - x1)
                                )
                        else:
                            # No pose detected
                            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (128, 128, 128), 2)
                            draw_text_with_background(
                                display_frame, f"Person #{track_id + 1} (No Pose)",
                                (x1, y1 - 10), font_scale=0.5, text_color=(128, 128, 128)
                            )
            
            # Draw frame info
            info_y = 30
            draw_text_with_background(
                display_frame, f"Frame: {frame_count}/{total_frames}",
                (10, info_y), font_scale=0.7
            )
            info_y += 30
            
            # Calculate FPS
            elapsed = time.time() - start_time
            current_fps = frame_count / elapsed if elapsed > 0 else 0
            draw_text_with_background(
                display_frame, f"FPS: {current_fps:.1f}",
                (10, info_y), font_scale=0.7
            )
            info_y += 30
            
            # Draw statistics
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
            
            # Draw legend
            legend_x = width - 150
            legend_y = 30
            cv2.rectangle(display_frame, (legend_x - 5, legend_y - 25), 
                         (width - 5, legend_y + 75), COLOR_BG, -1)
            
            cv2.putText(display_frame, "RISK LEVELS:", (legend_x, legend_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)
            legend_y += 25
            cv2.rectangle(display_frame, (legend_x, legend_y - 10), 
                         (legend_x + 15, legend_y), COLOR_SAFE, -1)
            cv2.putText(display_frame, "SAFE", (legend_x + 20, legend_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_TEXT, 1)
            legend_y += 20
            cv2.rectangle(display_frame, (legend_x, legend_y - 10), 
                         (legend_x + 15, legend_y), COLOR_WARNING, -1)
            cv2.putText(display_frame, "WARNING", (legend_x + 20, legend_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_TEXT, 1)
            legend_y += 20
            cv2.rectangle(display_frame, (legend_x, legend_y - 10), 
                         (legend_x + 15, legend_y), COLOR_DANGER, -1)
            cv2.putText(display_frame, "DANGER", (legend_x + 20, legend_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_TEXT, 1)
            
            # Save frame
            if SAVE_OUTPUT and out is not None:
                out.write(display_frame)
            
            # Display frame
            if DISPLAY_WINDOW:
                cv2.imshow('Pose + LSTM Analysis', display_frame)
                
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
            # Paused - just wait for key
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
    print(f"\nRisk Distribution:")
    print(f"  SAFE frames: {stats['safe_frames']}")
    print(f"  WARNING frames: {stats['warning_frames']}")
    print(f"  DANGER frames: {stats['danger_frames']}")
    print(f"\nPerformance:")
    elapsed = time.time() - start_time
    print(f"  Total time: {elapsed:.1f} seconds")
    print(f"  Average FPS: {frame_count / elapsed:.1f}")
    
    if SAVE_OUTPUT:
        print(f"\n✅ Output saved to: {OUTPUT_PATH}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Video Analysis - Pose + LSTM')
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
