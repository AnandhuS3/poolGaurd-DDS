"""
Configuration settings for PoolGuard
"""

import os
from pathlib import Path

# ============================================================================
# IMPORT CREDENTIALS FROM SECURE FILE
# ============================================================================
# Credentials are stored in credentials.py which loads from .env
# This keeps sensitive data separate and secure
from core.credentials import (
    DB_USER, DB_PASSWORD,
    SMTP_USERNAME, SMTP_PASSWORD,
    NOTIFICATION_RECIPIENTS,
    APP_BASE_URL,
    ALLOWED_ORIGINS,
)

# ============================================================================
# BASE DIRECTORIES
# ============================================================================
# BASE_DIR is the project root (v5-poss/), three levels up from this file:
#   config.py → core/ → backend/ → v5-poss/
BASE_DIR = Path(__file__).parent.parent.parent
UPLOAD_DIR = BASE_DIR / "assets" / "uploads"
MODEL_DIR = BASE_DIR / "assets" / "weights"  # Models are in assets/weights/
FRONTEND_DIR = BASE_DIR / "frontend"

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
# PostgreSQL database settings for authentication and alerting
# DB_USER and DB_PASSWORD imported from credentials.py
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "poolguard_db"
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))  # Connection pool size (raised from 5 for prod)

# ============================================================================
# SERVER SETTINGS
# ============================================================================
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

# Legacy compatibility
SERVER_HOST = HOST
SERVER_PORT = PORT

# ============================================================================
# MODEL SETTINGS
# ============================================================================
MODEL_PATH = MODEL_DIR / "best.pt"
MODEL_PATH_SECONDARY = MODEL_DIR / "best1.pt"  # Secondary model for ensemble
USE_ENSEMBLE = True   # Enable ensemble detection (uses both models for higher accuracy)
FALLBACK_MODEL = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.45  # Raised back up: 0.35 caused many false detections on land
YOLO_IMG_SIZE = 640          # Force YOLO to default size for speed boost (was full 1920/1080)

# Detection Classes
# Update these based on your trained model
DROWNING_CLASS_ID = 1  # Class ID for drowning detection
PERSON_CLASS_ID = 0    # Class ID for person detection

# ============================================================================
# PROCESSING SETTINGS
# ============================================================================
SKIP_FRAMES = 2  # Process every 2nd frame — better temporal resolution for pool detection
JPEG_QUALITY = 75  # (was 90). Faster encoding and lower latency for WebSocket streaming.

# Motion Detection (Smart Frame Skipping)
USE_MOTION_DETECTION = True  # Enable motion-based frame skipping
MOTION_THRESHOLD = 800       # Raised back up: 600 was too sensitive, caused unnecessary processing

# Legacy compatibility
FRAME_SKIP = SKIP_FRAMES
MAX_UPLOAD_SIZE_MB = 500  # Maximum video upload size

# ============================================================================
# DETECTION THRESHOLDS (in frames)
# ============================================================================
WARNING_THRESHOLD = 20  # Frames before WARNING state (~0.67s @ 30fps) — reduce false positives
DANGER_THRESHOLD = 45   # Frames before DANGER state (~1.5s @ 30fps) — needs sustained distress

# Legacy compatibility (convert frames to seconds assuming 30 FPS)
WARNING_DURATION_SEC = WARNING_THRESHOLD / 30
DROWNING_DURATION_SEC = DANGER_THRESHOLD / 30

# ============================================================================
# TRACKING SETTINGS
# ============================================================================
MAX_TRACK_AGE = 45  # Frames before removing lost tracks (was 60)

# Legacy DeepSORT compatibility
MAX_AGE = MAX_TRACK_AGE
N_INIT = 3                # Require 3 consistent detections before confirming track — prevents land-person false alarms
MAX_COSINE_DISTANCE = 0.35 # (was 0.5). Lowered back down to prevent bounding boxes from jumping between two different people.
NMS_MAX_OVERLAP = 0.6     # (was 0.7). Stronger duplicate bounding box removal.

# ============================================================================
# CORS SETTINGS
# ============================================================================
CORS_ORIGINS = ["*"]  # For production, specify exact origins

# ============================================================================
# COLORS (BGR format)
# ============================================================================
COLOR_SAFE = (0, 255, 0)      # Green
COLOR_WARNING = (0, 165, 255) # Orange
COLOR_DANGER = (0, 0, 255)    # Red

# ============================================================================
# REMOTE NOTIFICATION SYSTEM
# ============================================================================
# Enable external notifications for drowning alerts
NOTIFICATION_ENABLED = True  # Set to True to enable notifications

# Notification type: "email", "sms", or "whatsapp"
NOTIFICATION_TYPE = "email"

# Camera/Source identifier for notifications
CAMERA_NAME = "Main Pool Camera"

# Firebase Admin SDK — path to service account JSON
# Download from Firebase Console > Project Settings > Service Accounts
# Set GOOGLE_APPLICATION_CREDENTIALS env var OR put path here.
FIREBASE_SA_PATH = os.getenv("FIREBASE_SA_PATH", "")

# Email Configuration (SMTP)
# SMTP_USERNAME and SMTP_PASSWORD imported from credentials.py
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_FROM_EMAIL = ""  # Sender email (defaults to SMTP_USERNAME if empty)

# Recipients - imported from credentials.py
# NOTIFICATION_RECIPIENTS loaded from .env file

# ============================================================================
# POSE ESTIMATION SETTINGS (NEW - Pose-Driven Detection)
# ============================================================================
# Enable pose-driven behavior classification (set to False to use legacy heuristic)
USE_POSE_ESTIMATION = True

# Pose model configuration
POSE_MODEL_TYPE = "yolov8-pose"  # Options: "yolov8-pose", "mediapipe"
POSE_MODEL_PATH = MODEL_DIR / "yolov8n-pose.pt"  # Nano model is fastest
POSE_CONFIDENCE_THRESHOLD = 0.25  # Rebalanced (was 0.2). Prevents "ghost" skeletons which ruin LSTM accuracy.

# Fallback behavior
FALLBACK_TO_HEURISTIC = True  # Use position-based detection if pose fails

# ============================================================================
# BEHAVIOR CLASSIFICATION SETTINGS (NEW)
# ============================================================================
# Temporal analysis window
TEMPORAL_WINDOW_SIZE = 45  # Frames in sliding window (was 90 → faster responsiveness)
BEHAVIOR_UPDATE_INTERVAL = 1  # Classify behavior every N frames (1 = every frame)

# Behavior detection thresholds
THRASHING_THRESHOLD = 0.3  # Lowered: catch subtle struggling earlier (was 0.4)
STILLNESS_THRESHOLD = 20  # Frames of minimal movement for drowning (was 60 — too slow)
VERTICAL_ORIENTATION_THRESHOLD = 50  # Degrees from horizontal for struggling (was 60)

# Enhanced state transition thresholds (in frames)
ATTENTION_THRESHOLD = 5   # Frames before ATTENTION state (was 15 → react faster)
# WARNING_THRESHOLD and DANGER_THRESHOLD already defined above (legacy compatibility)

# Visualization (debug mode)
VISUALIZE_POSE = False  # Draw pose skeleton on output frames (adds overhead)
VISUALIZE_BEHAVIOR = True  # Show behavior labels on output

# ============================================================================
# SECONDARY POSE MODEL & LSTM INFERENCE (NEW)
# ============================================================================
# Secondary pose inference (non-blocking, CPU-only)
USE_SECONDARY_POSE = True  # Enable secondary pose model for LSTM
SECONDARY_POSE_MODEL_PATH = MODEL_DIR / "behavior" / "yolov8n-pose.pt"
SECONDARY_POSE_RESIZE = 320  # (was 512). Massive speed boost for LSTM pose extraction.
SECONDARY_POSE_FRAME_SKIP = 3  # (was 2). Process LSTM every 3rd frame.

# LSTM temporal classifier
USE_LSTM_CLASSIFIER = True  # Enable LSTM-based risk classification
LSTM_MODEL_PATH = MODEL_DIR / "behavior" / "drowning_lstm.pt"
LSTM_BUFFER_SIZE = 90  # 3 seconds @ 30 FPS
LSTM_MIN_FRAMES = 30  # Minimum frames before inference (1 second)
LSTM_DEVICE = 'cpu'  # Force CPU for LSTM (lightweight model)

# Risk scoring
LSTM_DANGER_THRESHOLD = 0.55  # Danger probability threshold (was 0.7 — too conservative)
LSTM_WARNING_THRESHOLD = 0.3  # Warning probability threshold (was 0.4)

# ============================================================================

