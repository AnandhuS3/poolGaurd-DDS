import cv2
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import numpy as np
import os
import time
import base64
import asyncio

# Import centralized logging configuration
from core.logging_config import loggers, log_video_processing, log_state_change, log_error
logger = loggers['video']
model_logger = loggers['model']
detection_logger = loggers['detection']
state_logger = loggers['state']

# REMOTE NOTIFICATION
try:
    from core.notifications import create_notification_service
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    logger.warning("[NOTIFICATION] Module not available - notifications disabled")

try:
    from core.config import *
except ImportError:
    # Default values if config.py doesn't exist
    MODEL_PATH = "weights/best.pt"
    MODEL_PATH_SECONDARY = "weights/best1.pt"
    USE_ENSEMBLE = True
    CONFIDENCE_THRESHOLD = 0.5
    DROWNING_CLASS_ID = 1
    DROWNING_DURATION_SEC = 5
    MAX_AGE = 30
    N_INIT = 3
    MAX_COSINE_DISTANCE = 0.3
    NMS_MAX_OVERLAP = 1.0
    JPEG_QUALITY = 85
    COLOR_SAFE = (0, 255, 0)
    COLOR_WARNING = (0, 165, 255)
    COLOR_DANGER = (0, 0, 255)
    MOTION_THRESHOLD = 1500
    USE_MOTION_DETECTION = True
    # REMOTE NOTIFICATION - defaults
    NOTIFICATION_ENABLED = False
    NOTIFICATION_TYPE = "email"
    CAMERA_NAME = "Main Pool Camera"
    NOTIFICATION_RECIPIENTS = []
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = ""
    SMTP_PASSWORD = ""
    SMTP_FROM_EMAIL = ""

# REMOTE NOTIFICATION - Initialize notification service
if NOTIFICATIONS_AVAILABLE and NOTIFICATION_ENABLED:
    notification_config = {
        "NOTIFICATION_ENABLED": NOTIFICATION_ENABLED,
        "NOTIFICATION_TYPE": NOTIFICATION_TYPE,
        "CAMERA_NAME": CAMERA_NAME,
        "NOTIFICATION_RECIPIENTS": NOTIFICATION_RECIPIENTS,
        "SMTP_SERVER": SMTP_SERVER,
        "SMTP_PORT": SMTP_PORT,
        "SMTP_USERNAME": SMTP_USERNAME,
        "SMTP_PASSWORD": SMTP_PASSWORD,
        "SMTP_FROM_EMAIL": SMTP_FROM_EMAIL,
    }
    notification_service = create_notification_service(notification_config)
    logger.info("[NOTIFICATION] Service enabled and initialized")
else:
    notification_service = None
    if NOTIFICATION_ENABLED:
        logger.warning("[NOTIFICATION] Enabled in config but module not available")

# Validate configuration
def validate_config():
    """Validate configuration parameters at startup"""
    errors = []
    
    # Model paths
    if not os.path.exists(MODEL_PATH):
        errors.append(f"Primary model not found: {MODEL_PATH}")
    
    if USE_ENSEMBLE and not os.path.exists(MODEL_PATH_SECONDARY):
        print(f"⚠️  Warning: Ensemble enabled but secondary model not found: {MODEL_PATH_SECONDARY}")
        print("    Continuing with single model")
    
    # Detection parameters
    if not 0.0 <= CONFIDENCE_THRESHOLD <= 1.0:
        errors.append(f"CONFIDENCE_THRESHOLD must be 0.0-1.0, got: {CONFIDENCE_THRESHOLD}")
    
    if DROWNING_CLASS_ID < 0:
        errors.append(f"DROWNING_CLASS_ID must be >= 0, got: {DROWNING_CLASS_ID}")
    
    # Timing parameters
    if DROWNING_DURATION_SEC <= 0:
        errors.append(f"DROWNING_DURATION_SEC must be > 0, got: {DROWNING_DURATION_SEC}")
    
    # Tracking parameters
    if MAX_AGE <= 0:
        errors.append(f"MAX_AGE must be > 0, got: {MAX_AGE}")
    
    if N_INIT <= 0:
        errors.append(f"N_INIT must be > 0, got: {N_INIT}")
    
    if not 0.0 <= MAX_COSINE_DISTANCE <= 1.0:
        errors.append(f"MAX_COSINE_DISTANCE must be 0.0-1.0, got: {MAX_COSINE_DISTANCE}")
    
    if not 0.0 <= NMS_MAX_OVERLAP <= 1.0:
        errors.append(f"NMS_MAX_OVERLAP must be 0.0-1.0, got: {NMS_MAX_OVERLAP}")
    
    # Video processing
    if JPEG_QUALITY < 1 or JPEG_QUALITY > 100:
        errors.append(f"JPEG_QUALITY must be 1-100, got: {JPEG_QUALITY}")
    
    # Raise error if any validation failed
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)
    
    logger.info("[OK] Configuration validated successfully")

# Run validation before loading models
validate_config()

# Load YOLO models - ensemble for better accuracy
# Load model with GPU acceleration
try:
    model = YOLO(MODEL_PATH)
    # Explicitly set device to GPU if available
    if hasattr(model, 'device'):
        model.to('cuda' if __import__('torch').cuda.is_available() else 'cpu')
    logger.info(f"[OK] Loaded primary model: {MODEL_PATH}")
    logger.info(f"[OK] Using device: {'cuda' if __import__('torch').cuda.is_available() else 'cpu'}")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    raise

# Load secondary model if ensemble is enabled
model_secondary = None
if USE_ENSEMBLE and os.path.exists(MODEL_PATH_SECONDARY):
    try:
        model_secondary = YOLO(MODEL_PATH_SECONDARY)
        if hasattr(model_secondary, 'device'):
            model_secondary.to('cuda' if __import__('torch').cuda.is_available() else 'cpu')
        logger.info(f"[OK] Loaded secondary model: {MODEL_PATH_SECONDARY}")
        print("[OK] Ensemble detection enabled (using both models for higher accuracy)")
    except Exception as e:
        print(f"[WARNING] Failed to load secondary model: {e}")
        print("[INFO] Continuing with single model")
elif not USE_ENSEMBLE:
    print("[INFO] Ensemble mode disabled in config")
else:
    logger.warning(f"[WARNING] Secondary model not found: {MODEL_PATH_SECONDARY}. Using single model.")

# NOTE: DeepSORT tracker is created inside process_video_realtime() per session.
# Module-level tracker was removed to prevent track-ID contamination across sessions.

# ============================================================================
# POSE-DRIVEN DETECTION PIPELINE (NEW)
# ============================================================================
# Initialize pose-driven processor if enabled
try:
    from core.pose_driven_processor import PoseDrivenProcessor
    from core import config as config_module
    
    pose_processor = PoseDrivenProcessor(config_module)
    
    if pose_processor.is_available():
        logger.info("✅ Pose-driven detection pipeline enabled")
        logger.info(f"   Model: {POSE_MODEL_TYPE}")
        logger.info(f"   Temporal window: {TEMPORAL_WINDOW_SIZE} frames")
        logger.info(f"   Fallback: {'Enabled' if FALLBACK_TO_HEURISTIC else 'Disabled'}")
    else:
        logger.info("⚠️  Pose-driven detection not available - using legacy heuristic")
        pose_processor = None
        
except Exception as e:
    logger.warning(f"Failed to initialize pose-driven pipeline: {e}")
    logger.info("Using legacy heuristic detection")
    pose_processor = None

# ============================================================================
# SECONDARY POSE MODEL & LSTM INFERENCE (NEW)
# ============================================================================
# Initialize secondary pose detector and LSTM risk inference
lstm_inference_engine = None

if USE_SECONDARY_POSE and USE_LSTM_CLASSIFIER:
    try:
        from core.behavior.inference import RiskInferenceEngine
        from core.pose_estimation.pose_detector import PoseDetector
        import cv2
        
        # Initialize secondary pose detector (CPU-only, lightweight)
        secondary_pose_detector = PoseDetector(
            model_type="yolov8-pose",
            model_path=str(SECONDARY_POSE_MODEL_PATH) if SECONDARY_POSE_MODEL_PATH else None,
            confidence_threshold=POSE_CONFIDENCE_THRESHOLD,
            device='cpu'  # Force CPU for secondary model
        )
        
        # Initialize LSTM risk inference engine
        lstm_inference_engine = RiskInferenceEngine(
            model_path=str(LSTM_MODEL_PATH) if LSTM_MODEL_PATH else None,
            buffer_size=LSTM_BUFFER_SIZE,
            min_frames=LSTM_MIN_FRAMES,
            device=LSTM_DEVICE
        )
        
        # Create dummy LSTM model if not exists
        if not LSTM_MODEL_PATH.exists():
            logger.warning(f"LSTM model not found at {LSTM_MODEL_PATH}")
            logger.info("Creating dummy LSTM model for testing...")
            from core.behavior.temporal_model import create_dummy_model
            create_dummy_model(LSTM_MODEL_PATH)
            # Reload inference engine
            lstm_inference_engine = RiskInferenceEngine(
                model_path=str(LSTM_MODEL_PATH),
                buffer_size=LSTM_BUFFER_SIZE,
                min_frames=LSTM_MIN_FRAMES,
                device=LSTM_DEVICE
            )
        
        if lstm_inference_engine.is_available() and secondary_pose_detector.is_available():
            logger.info("✅ LSTM risk inference enabled")
            logger.info(f"   Secondary pose model: {SECONDARY_POSE_MODEL_PATH}")
            logger.info(f"   LSTM model: {LSTM_MODEL_PATH}")
            logger.info(f"   Buffer size: {LSTM_BUFFER_SIZE} frames")
            logger.info(f"   Frame skip: 1:{SECONDARY_POSE_FRAME_SKIP}")
            logger.info(f"   Resize: {SECONDARY_POSE_RESIZE}px")
        else:
            logger.warning("⚠️  LSTM inference not available - disabled")
            lstm_inference_engine = None
            secondary_pose_detector = None
            
    except Exception as e:
        logger.warning(f"Failed to initialize LSTM inference: {e}")
        logger.info("LSTM risk scoring disabled")
        lstm_inference_engine = None
        secondary_pose_detector = None
else:
    secondary_pose_detector = None
    logger.info("LSTM inference disabled in config")

async def process_video_realtime(video_path, websocket, external_notification_service=None):
    """Process video with real-time streaming via WebSocket - UPGRADED
    
    Args:
        video_path: Path to the video file or RTSP URL
        websocket: WebSocket connection to stream frames to
        external_notification_service: Optional database-aware NotificationService from app.py.
            If provided, this is used instead of the module-level config-based one,
            enabling FCM push notifications, database alert records, and escalation to admin.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        await websocket.send_json({
            "type": "error",
            "message": "Could not open video"
        })
        raise ValueError("Could not open video stream")

    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Calculate frame-based thresholds for drowning detection
    fps = max(fps, 1)  # Prevent division by zero
    drowning_threshold_frames = int(DROWNING_DURATION_SEC * fps)
    warning_threshold_frames = int(WARNING_DURATION_SEC * fps)

    logger.info(f"Starting real-time video processing: {video_path}")
    logger.info(f"Video properties: {width}x{height} @ {fps} FPS, {total_frames} frames")
    logger.info(f"Drowning thresholds: {drowning_threshold_frames} frames ({DROWNING_DURATION_SEC}s), Warning: {warning_threshold_frames} frames")

    # Create a fresh DeepSORT tracker for this session.
    # CRITICAL: must NOT be module-level; a shared tracker causes track-ID bleed
    # between separate video sessions (person #5 from session A re-appears in session B).
    tracker = DeepSort(
        max_age=MAX_AGE,
        n_init=N_INIT,
        nms_max_overlap=NMS_MAX_OVERLAP,
        max_cosine_distance=MAX_COSINE_DISTANCE
    )
    logger.info("[TRACKER] Fresh DeepSORT tracker created for this session")

    # Reset pose-driven processor per-track state (temporal buffers, state machines).
    if pose_processor:
        pose_processor.reset()
        logger.info("[POSE] Pose processor state reset for new session")

    # Reset LSTM per-track buffers so stale keypoint sequences don't pollute new video.
    if lstm_inference_engine:
        lstm_inference_engine.track_buffers.clear()
        logger.info("[LSTM] Inference buffers cleared for new session")

    # Tracking data - UPGRADED: Cleaner structure
    person_data = {}
    frame_count = 0
    
    # Dynamic frame skipping for real-time processing
    base_frame_skip = FRAME_SKIP
    if fps > 30:
        frame_skip = max(base_frame_skip, int(fps / 30 * base_frame_skip))
        logger.info(f"High FPS detected ({fps}): Adjusting frame skip to {frame_skip}")
    else:
        frame_skip = base_frame_skip
    
    logger.info(f"Frame skip rate: {frame_skip} (processing every {frame_skip}th frame)")
    
    # Performance monitoring
    process_start_time = time.time()
    processed_frame_count = 0
    last_fps_update = time.time()
    processing_fps = 0.0
    
    # Motion detection for smart frame clustering
    prev_gray = None
    last_detections = []
    frames_since_motion = 0
    skipped_frames = 0

    try:
        empty_frames = 0
        frame_start_time = time.time()  # real-time pacing reference
        while cap.isOpened():
            # Offload synchronous OpenCV read to a background thread to prevent blocking FastAPI's event loop
            ret, frame = await asyncio.to_thread(cap.read)
            if not ret:
                empty_frames += 1
                if empty_frames > 30:
                    # 30 consecutive read failures — stream is gone. Break cleanly
                    # so the BackgroundCameraManager retry loop can reconnect.
                    logger.warning("[VIDEO] 30 consecutive empty frames — stream ended, will retry.")
                    break
                await asyncio.sleep(0.05)  # brief wait before next read attempt
                continue
            else:
                empty_frames = 0

            frame_count += 1
            
            # Skip frames if needed for performance
            if frame_count % frame_skip != 0:
                continue
                
            start_time = time.time()
            
            # Motion detection - skip processing if minimal motion
            skip_ml_processing = False
            if USE_MOTION_DETECTION:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_gray is not None:
                    frame_diff = cv2.absdiff(prev_gray, gray)
                    motion_score = np.sum(frame_diff)
                    
                    if motion_score < MOTION_THRESHOLD and len(last_detections) > 0 and frames_since_motion < 15:
                        skip_ml_processing = True
                        skipped_frames += 1
                        detections = last_detections
                    else:
                        frames_since_motion = 0
                else:
                    frames_since_motion = 0
                
                prev_gray = gray
            
            # Run ML detection only if motion detected or required
            if not skip_ml_processing:
                # Offload heavy ML inference to background threads to prevent FastAPI event loop blocking
                # YOLO detection with ensemble (if secondary model available)
                results = await asyncio.to_thread(model, frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
                
                # Run secondary model for ensemble detection
                results_secondary = None
                if model_secondary:
                    results_secondary = await asyncio.to_thread(model_secondary, frame, conf=CONFIDENCE_THRESHOLD, verbose=False)

                # Prepare detections for DeepSORT
                detections = []
            
                # Process primary model results
                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        detections.append(([x1, y1, x2 - x1, y2 - y1], conf, cls))
                
                # Add secondary model detections (ensemble approach)
                if results_secondary:
                    for result in results_secondary:
                        for box in result.boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            conf = float(box.conf[0])
                            cls = int(box.cls[0])
                            # Boost ensemble confidence slightly; cap at 1.0
                            detections.append(([x1, y1, x2 - x1, y2 - y1], min(conf * 1.1, 1.0), cls))
                
                # Cache detections for motion-based reuse
                last_detections = detections.copy()
            else:
                # Using cached detections from previous frame
                frames_since_motion += 1

            # Update tracker - DeepSORT handles ID persistence
            tracks = tracker.update_tracks(detections, frame=frame)

            # ====================================================================
            # POSE-DRIVEN ANALYSIS (NEW) with Heuristic Fallback
            # ====================================================================
            pose_results = {}
            if pose_processor and pose_processor.is_available():
                try:
                    # Run pose-driven analysis for all tracks
                    pose_results = pose_processor.process_tracks(
                        frame, tracks, frame_count, height, width
                    )
                except Exception as e:
                    logger.warning(f"Pose-driven analysis failed: {e}")
                    pose_results = {}

            # ====================================================================
            # LSTM RISK INFERENCE (NEW) - Secondary pose model with frame skip
            # ====================================================================
            lstm_risk_results = {}
            
            if (lstm_inference_engine and secondary_pose_detector and 
                lstm_inference_engine.is_available()):
                
                # Frame skip: Process every Nth frame
                if frame_count % SECONDARY_POSE_FRAME_SKIP == 0:
                    try:
                        # Resize frame for faster inference
                        scale = SECONDARY_POSE_RESIZE / max(width, height)
                        resized_width = int(width * scale)
                        resized_height = int(height * scale)
                        resized_frame = cv2.resize(frame, (resized_width, resized_height))
                        
                        # Extract bounding boxes for confirmed tracks
                        bboxes_for_lstm = []
                        track_ids_for_lstm = []
                        
                        for track in tracks:
                            if not track.is_confirmed():
                                continue
                            
                            ltrb = track.to_ltrb()
                            x1, y1, x2, y2 = map(int, ltrb)
                            
                            # Scale bbox to resized frame
                            x1_scaled = int(x1 * scale)
                            y1_scaled = int(y1 * scale)
                            x2_scaled = int(x2 * scale)
                            y2_scaled = int(y2 * scale)
                            
                            bboxes_for_lstm.append((x1_scaled, y1_scaled, x2_scaled, y2_scaled))
                            track_ids_for_lstm.append(track.track_id)
                        
                        # Detect poses on resized frame
                        if len(bboxes_for_lstm) > 0:
                            poses = secondary_pose_detector.detect_poses(resized_frame, bboxes_for_lstm)
                            
                            # Process each pose with LSTM inference
                            for track_id, pose, bbox_scaled in zip(track_ids_for_lstm, poses, bboxes_for_lstm):
                                if pose and 'keypoints' in pose:
                                    keypoints = pose['keypoints']
                                    
                                    # Run LSTM inference
                                    risk_result = lstm_inference_engine.process_track(
                                        track_id=track_id,
                                        keypoints=keypoints,
                                        bbox=bbox_scaled,
                                        frame_height=resized_height,
                                        frame_number=frame_count
                                    )
                                    
                                    lstm_risk_results[track_id] = risk_result
                        
                    except Exception as e:
                        logger.warning(f"LSTM inference failed: {e}")
                        lstm_risk_results = {}

            # Analyze each track
            tracked_persons = []
            
            for track in tracks:
                if not track.is_confirmed():
                    continue

                track_id = track.track_id
                ltrb = track.to_ltrb()  # left, top, right, bottom
                x1, y1, x2, y2 = map(int, ltrb)
                cls = track.get_det_class() if hasattr(track, 'get_det_class') else 0

                # Initialize person data if new
                if track_id not in person_data:
                    person_data[track_id] = {
                        "state": "SAFE",
                        "behavior": "unknown",  # Behavior type from pose-driven
                        "frames_underwater": 0,
                        "warning_start_frame": None,
                        "danger_start_frame": None,
                        "frames": 0,
                        "alert_sent": False,
                        "warning_alert_sent": False,
                        "last_seen": frame_count,
                        "previous_state": "SAFE",
                        "bbox": [x1, y1, x2, y2],
                        "confidence": 0.0,
                        "pose_available": False,
                        # LSTM risk scoring (NEW)
                        "lstm_risk_state": "SAFE",
                        "lstm_risk_scores": [1.0, 0.0, 0.0],  # [SAFE, WARNING, DANGER]
                        "lstm_confidence": 1.0,
                        "lstm_available": False
                    }

                person_data[track_id]["frames"] += 1
                person_data[track_id]["last_seen"] = frame_count
                person_data[track_id]["bbox"] = [x1, y1, x2, y2]
                
                current_state = person_data[track_id]["state"]
                previous_state = person_data[track_id]["previous_state"]
                
                # ============================================================
                # DUAL-MODE DETECTION: Pose-Driven OR Heuristic
                # ============================================================
                use_pose_driven = False
                
                # Try pose-driven detection first
                if track_id in pose_results and pose_results[track_id]['pose_available']:
                    use_pose_driven = True
                    pose_result = pose_results[track_id]
                    
                    # Convert PersonState enum to string
                    from core.behavior_classification import PersonState
                    state_map = {
                        PersonState.SAFE: "SAFE",
                        PersonState.ATTENTION: "ATTENTION",
                        PersonState.WARNING: "WARNING",
                        PersonState.DANGER: "DANGER"
                    }
                    new_state = state_map.get(pose_result['state'], "SAFE")
                    
                    # Update person data with pose-driven results
                    person_data[track_id]["state"] = new_state
                    person_data[track_id]["behavior"] = pose_result['behavior'].value
                    person_data[track_id]["confidence"] = pose_result['confidence']
                    person_data[track_id]["pose_available"] = True
                    
                    # Track state transitions
                    if new_state == "WARNING" and person_data[track_id]["warning_start_frame"] is None:
                        person_data[track_id]["warning_start_frame"] = frame_count
                    elif new_state == "DANGER" and person_data[track_id]["danger_start_frame"] is None:
                        person_data[track_id]["danger_start_frame"] = frame_count
                    
                    logger.debug(f"[POSE] Person #{track_id}: {new_state} (behavior: {pose_result['behavior'].value})")
                
                # Fallback to heuristic detection
                elif FALLBACK_TO_HEURISTIC:
                    # Legacy position-based drowning detection
                    person_bottom = y2
                    position_ratio = person_bottom / height
                    
                    if position_ratio > 0.6:
                        person_data[track_id]["frames_underwater"] += 1
                    else:
                        # Decrement counter when in safe position
                        person_data[track_id]["frames_underwater"] = max(0, person_data[track_id]["frames_underwater"] - 2)
                    
                    # State transitions based on frames_underwater
                    frames_underwater = person_data[track_id]["frames_underwater"]
                    
                    if frames_underwater >= drowning_threshold_frames:
                        # DANGER state
                        if current_state != "DANGER":
                            person_data[track_id]["state"] = "DANGER"
                            person_data[track_id]["danger_start_frame"] = frame_count
                            logger.critical(f"[HEURISTIC] Person #{track_id}: {current_state} → DANGER (underwater {frames_underwater} frames)")
                    
                    elif frames_underwater >= warning_threshold_frames:
                        # WARNING state
                        if current_state == "SAFE":
                            person_data[track_id]["state"] = "WARNING"
                            person_data[track_id]["warning_start_frame"] = frame_count
                            logger.warning(f"[HEURISTIC] Person #{track_id}: SAFE → WARNING (underwater {frames_underwater} frames)")
                        elif current_state == "DANGER":
                            # Stay in DANGER (sticky state)
                            pass
                    
                    else:
                        # SAFE state (only if not in DANGER)
                        if current_state == "WARNING":
                            person_data[track_id]["state"] = "SAFE"
                            person_data[track_id]["warning_start_frame"] = None
                            logger.info(f"[HEURISTIC] Person #{track_id}: WARNING → SAFE (recovered)")
                        elif current_state == "SAFE":
                            # Already safe
                            pass
                        # DANGER state is sticky - no auto-recovery
                
                # ============================================================
                # END DUAL-MODE DETECTION
                # ============================================================
                
                # ============================================================
                # UPDATE LSTM RISK SCORES (NEW)
                # ============================================================
                # Update person data with LSTM risk assessment if available
                if track_id in lstm_risk_results:
                    lstm_result = lstm_risk_results[track_id]
                    person_data[track_id]["lstm_risk_state"] = lstm_result['risk_state']
                    person_data[track_id]["lstm_risk_scores"] = lstm_result['risk_scores']
                    person_data[track_id]["lstm_confidence"] = lstm_result['confidence']
                    person_data[track_id]["lstm_available"] = True
                    
                    # Optionally override state based on LSTM if confidence is high
                    if lstm_result['confidence'] > 0.8 and lstm_result['inference_ready']:
                        # High confidence LSTM prediction can influence state
                        lstm_state = lstm_result['risk_state']
                        
                        # Only escalate state, never de-escalate (safety first)
                        if lstm_state == "DANGER" and person_data[track_id]["state"] != "DANGER":
                            logger.warning(f"[LSTM] Person #{track_id}: LSTM high-confidence DANGER override (conf={lstm_result['confidence']:.2f})")
                            person_data[track_id]["state"] = "DANGER"
                
                    # DANGER state is sticky - no auto-recovery

                # Detect state changes and emit events
                new_state = person_data[track_id]["state"]
                if new_state != previous_state:
                    person_data[track_id]["previous_state"] = new_state
                    
                    # Emit state change event via WebSocket
                    state_change_event = {
                        "type": "state_change",
                        "person_id": track_id,
                        "old_state": previous_state,
                        "new_state": new_state,
                        "timestamp": time.time(),
                        "frames_underwater": person_data[track_id].get("frames_underwater", 0)
                    }
                    
                    await websocket.send_json(state_change_event)
                    logger.info(f"[STATE CHANGE] Person #{track_id}: {previous_state} → {new_state}")
                    
                    # REMOTE NOTIFICATION - Trigger external notification
                    if new_state in ["WARNING", "DANGER"]:
                        should_notify = False
                        
                        if new_state == "WARNING" and not person_data[track_id].get("warning_alert_sent", False):
                            person_data[track_id]["warning_alert_sent"] = True
                            should_notify = True
                        elif new_state == "DANGER" and not person_data[track_id]["alert_sent"]:
                            person_data[track_id]["alert_sent"] = True
                            should_notify = True
                        
                        if should_notify:
                            # Prefer the database-aware service injected from app.py (FCM + DB records).
                            # Fall back to the legacy config-based service if no external one is given.
                            active_svc = external_notification_service or notification_service
                            if active_svc:
                                await active_svc.send_alert(
                                    track_id=track_id,
                                    severity=new_state,
                                    camera_name=CAMERA_NAME
                                )
                            else:
                                logger.warning(
                                    f"[NOTIFICATION] No notification service available — "
                                    f"alert for Person #{track_id} ({new_state}) NOT sent. "
                                    "Check SMTP credentials in .env and NOTIFICATION_ENABLED in config.py."
                                )
                
                # NOTE: Bounding boxes and labels are drawn by the frontend canvas overlay.
                # Removing all OpenCV drawing here eliminates duplicate rendering and
                # reduces CPU overhead.  The raw frame is sent as-is; the frontend
                # BoundingOverlay draws clean, colour-coded boxes on a transparent canvas.

                # Add to tracked persons list
                # Safely get confidence value
                conf_value = track.get_det_conf() if hasattr(track, 'get_det_conf') else None
                confidence = float(conf_value) if conf_value is not None else 0.0
                
                # Use pose confidence if available, otherwise detection confidence
                final_confidence = person_data[track_id].get("confidence", confidence)
                
                tracked_persons.append({
                    "id": track_id,
                    "bbox": [x1, y1, x2, y2],
                    "status": new_state.lower(),
                    "state": new_state,
                    "alert": new_state == "DANGER",
                    "frames_underwater": person_data[track_id].get("frames_underwater", 0),
                    "confidence": final_confidence,
                    "behavior": person_data[track_id].get("behavior", "unknown"),
                    "pose_available": person_data[track_id].get("pose_available", False),
                    # LSTM risk scoring (NEW)
                    "lstm_risk_state": person_data[track_id].get("lstm_risk_state", "SAFE"),
                    "lstm_risk_scores": person_data[track_id].get("lstm_risk_scores", [1.0, 0.0, 0.0]),
                    "lstm_confidence": person_data[track_id].get("lstm_confidence", 0.0),
                    "lstm_available": person_data[track_id].get("lstm_available", False)
                })

            # Encode raw (unannotated) frame – frontend BoundingOverlay draws all overlays via canvas
            # Offloaded to thread as image encoding is CPU-heavy
            encode_success, buffer = await asyncio.to_thread(
                cv2.imencode, '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
            )
            if not encode_success:
                logger.warning(f"Failed to encode frame {frame_count}")
                continue
                
            analysis_frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Update performance metrics
            processed_frame_count += 1
            current_time = time.time()
            if current_time - last_fps_update >= 1.0:
                processing_fps = processed_frame_count / (current_time - process_start_time)
                last_fps_update = current_time

            # Send analysis frame via WebSocket
            await websocket.send_json({
                "type": "frame",
                "analysis_frame": analysis_frame_base64,
                "frame_number": frame_count,
                "total_frames": total_frames,
                "persons": tracked_persons,
                "performance": {
                    "processing_fps": round(processing_fps, 2),
                    "video_fps": fps,
                    "frame_skip": frame_skip,
                    "speed_ratio": round((processing_fps * frame_skip) / fps, 2) if fps > 0 else 0,
                    "real_time": (processing_fps * frame_skip) >= fps
                },
                "summary": {
                    "total": len(tracked_persons),
                    "safe": sum(1 for p in tracked_persons if p["status"] == "safe"),
                    "warning": sum(1 for p in tracked_persons if p["status"] == "warning"),
                    "danger": sum(1 for p in tracked_persons if p["status"] == "danger"),
                    "alerts": sum(1 for p in tracked_persons if p["alert"])
                }
            })
            
            # ── Real-time pacing ────────────────────────────────────────────
            # Sleep just enough so that frames reach the client at the video's
            # native FPS. Without this, the backend blasts all frames instantly,
            # which fills the browser's network buffer and causes severe lag.
            elapsed = time.time() - frame_start_time
            expected = frame_count / fps  # wall-clock seconds at which this frame should arrive
            pace_sleep = expected - elapsed
            if pace_sleep > 0:
                await asyncio.sleep(pace_sleep)

            # Log every 30 frames
            if frame_count % 30 == 0:
                print(f"Processed frame {frame_count}/{total_frames}, Persons: {len(tracked_persons)}")

    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": f"Processing error: {str(e)}"
        })
    finally:
        cap.release()

        logger.info("Video processing completed")
        # Send completion message
        completion_msg = {
            "type": "complete",
            "message": "Video processing completed",
            "total_persons": len(person_data),
            "person_data": {
                f"person_{k}": {
                    "status": v["state"].lower(),
                    "frames": v["frames"],
                    "frames_underwater": v.get("frames_underwater", 0),
                    "warning_frames": (v["danger_start_frame"] or v["last_seen"]) - (v["warning_start_frame"] or v["last_seen"]) if v.get("warning_start_frame") else 0,
                    "danger_frames": v["last_seen"] - (v["danger_start_frame"] or v["last_seen"]) if v.get("danger_start_frame") else 0
                }
                for k, v in person_data.items()
            }
        }
        if USE_MOTION_DETECTION and frame_count > 0:
            processed_frames = frame_count // frame_skip
            if processed_frames > 0:
                skip_percentage = (skipped_frames / processed_frames) * 100
                completion_msg["motion_stats"] = f"Skipped {skipped_frames}/{processed_frames} low-motion frames ({skip_percentage:.1f}% speed boost)"
        await websocket.send_json(completion_msg)