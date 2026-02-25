"""
Standalone video analysis test script
Tests drowning detection and bounding box tracking without frontend
"""
import cv2
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import numpy as np
import os
import time

try:
    from config import *
except ImportError:
    # Default values if config.py doesn't exist
    MODEL_PATH = "weights/best.pt"
    CONFIDENCE_THRESHOLD = 0.4
    DROWNING_CLASS_ID = 1
    DROWNING_DURATION_SEC = 5
    MAX_AGE = 30
    N_INIT = 3
    MAX_COSINE_DISTANCE = 0.3
    NMS_MAX_OVERLAP = 1.0
    COLOR_SAFE = (0, 255, 0)
    COLOR_WARNING = (0, 165, 255)
    COLOR_DANGER = (0, 0, 255)

print("="*60)
print("  DROWNING DETECTION SYSTEM - ANALYSIS TEST")
print("="*60)
print()

# Load YOLO model
print(f"[1/4] Loading YOLO model: {MODEL_PATH}")
if not os.path.exists(MODEL_PATH):
    print(f"❌ ERROR: Model file not found at {MODEL_PATH}")
    exit(1)
model = YOLO(MODEL_PATH)
print("✓ Model loaded successfully")
print()

# Initialize DeepSORT tracker
print("[2/4] Initializing DeepSORT tracker...")
tracker = DeepSort(
    max_age=MAX_AGE,
    n_init=N_INIT,
    nms_max_overlap=NMS_MAX_OVERLAP,
    max_cosine_distance=MAX_COSINE_DISTANCE
)
print("✓ Tracker initialized")
print()

# Get video path from user
print("[3/4] Video Selection")
print("Available options:")
print("  1. Enter custom video path")
print("  2. Use sample from uploads folder")
print()

# Check uploads folder
uploads_dir = "uploads"
if os.path.exists(uploads_dir) and os.path.isdir(uploads_dir):
    video_files = [f for f in os.listdir(uploads_dir) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    if video_files:
        print(f"Found {len(video_files)} video(s) in uploads folder:")
        for i, f in enumerate(video_files, 1):
            print(f"    {i}. {f}")
        print()

video_path = input("Enter video path or file number from uploads: ").strip()

# Handle file number selection
if video_path.isdigit() and video_files:
    idx = int(video_path) - 1
    if 0 <= idx < len(video_files):
        video_path = os.path.join(uploads_dir, video_files[idx])
    else:
        print("Invalid selection")
        exit(1)

# Verify video exists
if not os.path.exists(video_path):
    print(f"❌ ERROR: Video file not found: {video_path}")
    exit(1)

print(f"✓ Video selected: {video_path}")
print()

# Process video
print("[4/4] Processing Video")
print("-" * 60)

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("❌ ERROR: Could not open video file")
    exit(1)

# Get video properties
fps = int(cap.get(cv2.CAP_PROP_FPS))
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps if fps > 0 else 0

print(f"Video Properties:")
print(f"  Resolution: {width}x{height}")
print(f"  FPS: {fps}")
print(f"  Total Frames: {total_frames}")
print(f"  Duration: {duration:.2f} seconds")
print()

# Create output video writer
output_path = "output/test_analysis_output.mp4"
os.makedirs("output", exist_ok=True)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

# Tracking data
person_data = {}
frame_count = 0
detections_log = []

print("Processing frames...")
start_time = time.time()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    frame_count += 1
    
    # Show progress every 30 frames
    if frame_count % 30 == 0 or frame_count == 1:
        progress = (frame_count / total_frames) * 100
        print(f"  Frame {frame_count}/{total_frames} ({progress:.1f}%)", end='\r')
    
    # YOLO detection
    results = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
    
    # Prepare detections for DeepSORT
    detections = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            detections.append(([x1, y1, x2 - x1, y2 - y1], conf, cls))
    
    # Update tracker
    tracks = tracker.update_tracks(detections, frame=frame)
    
    # Analyze each track
    current_time = time.time()
    active_tracks = 0
    
    for track in tracks:
        if not track.is_confirmed():
            continue
        
        active_tracks += 1
        track_id = track.track_id
        ltrb = track.to_ltrb()
        cls = track.get_det_class() if hasattr(track, 'get_det_class') else 0
        
        # Initialize person data if new
        if track_id not in person_data:
            person_data[track_id] = {
                "status": "safe",
                "drowning_start": None,
                "frames": 0,
                "drowning_alert": False,
                "first_seen": frame_count,
                "last_seen": frame_count,
                "class_detections": {}
            }
        
        person_data[track_id]["frames"] += 1
        person_data[track_id]["last_seen"] = frame_count
        
        # Track class detections
        if cls not in person_data[track_id]["class_detections"]:
            person_data[track_id]["class_detections"][cls] = 0
        person_data[track_id]["class_detections"][cls] += 1
        
        # Check for drowning based on class ID
        if cls == DROWNING_CLASS_ID:
            if person_data[track_id]["drowning_start"] is None:
                person_data[track_id]["drowning_start"] = current_time
                person_data[track_id]["status"] = "warning"
            elif current_time - person_data[track_id]["drowning_start"] > DROWNING_DURATION_SEC:
                person_data[track_id]["status"] = "danger"
                if not person_data[track_id]["drowning_alert"]:
                    person_data[track_id]["drowning_alert"] = True
                    detections_log.append({
                        "frame": frame_count,
                        "track_id": track_id,
                        "event": "DROWNING ALERT",
                        "time": f"{frame_count/fps:.2f}s"
                    })
        else:
            person_data[track_id]["drowning_start"] = None
            person_data[track_id]["status"] = "safe"
        
        # Draw bounding box
        color = COLOR_SAFE
        if person_data[track_id]["status"] == "warning":
            color = COLOR_WARNING
        elif person_data[track_id]["status"] == "danger":
            color = COLOR_DANGER
        
        x1, y1, x2, y2 = map(int, ltrb)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Draw label with background
        label = f"ID:{track_id} {person_data[track_id]['status'].upper()}"
        if cls == DROWNING_CLASS_ID:
            label += " [DROWNING]"
        
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x1, y1 - label_size[1] - 10),
                     (x1 + label_size[0], y1), color, -1)
        cv2.putText(frame, label, (x1, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Add frame info
    info_text = f"Frame: {frame_count}/{total_frames} | Tracked: {active_tracks}"
    cv2.putText(frame, info_text, (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Write to output video
    out.write(frame)

# Cleanup
cap.release()
out.release()

processing_time = time.time() - start_time
print(f"\n  Frame {total_frames}/{total_frames} (100.0%)")
print()
print("="*60)
print("  ANALYSIS COMPLETE")
print("="*60)
print()

# Summary
print("Summary:")
print(f"  Processing Time: {processing_time:.2f} seconds")
print(f"  Average FPS: {total_frames/processing_time:.2f}")
print(f"  Total Persons Tracked: {len(person_data)}")
print()

# Detailed person data
if person_data:
    print("Tracked Persons Details:")
    print("-" * 60)
    for track_id, data in person_data.items():
        print(f"\n  Person ID: {track_id}")
        print(f"    First Seen: Frame {data['first_seen']} ({data['first_seen']/fps:.2f}s)")
        print(f"    Last Seen: Frame {data['last_seen']} ({data['last_seen']/fps:.2f}s)")
        print(f"    Total Frames: {data['frames']}")
        print(f"    Final Status: {data['status'].upper()}")
        print(f"    Drowning Alert: {'YES' if data['drowning_alert'] else 'NO'}")
        print(f"    Class Detections: {data['class_detections']}")

# Alert log
if detections_log:
    print()
    print("="*60)
    print("  DROWNING ALERTS")
    print("="*60)
    for log in detections_log:
        print(f"  ⚠️  Frame {log['frame']} ({log['time']}): Person {log['track_id']} - {log['event']}")

print()
print(f"✓ Output video saved to: {output_path}")
print()
print("To view the annotated video, run:")
print(f"  start {output_path}")
print()
