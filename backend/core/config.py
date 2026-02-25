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
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER, TWILIO_WHATSAPP_FROM,
    NOTIFICATION_RECIPIENTS
)

# ============================================================================
# BASE DIRECTORIES
# ============================================================================
# BASE_DIR is the project root (parent of core folder)
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
MODEL_DIR = BASE_DIR / "weights"  # Models are in the weights folder
FRONTEND_DIR = BASE_DIR / "frontend"

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
# MySQL database settings for authentication and alerting
# DB_USER and DB_PASSWORD imported from credentials.py
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "drowning_detection_db"
DB_POOL_SIZE = 5  # Connection pool size

# ============================================================================
# SERVER SETTINGS
# ============================================================================
HOST = "0.0.0.0"
PORT = 8000
DEBUG = True

# Legacy compatibility
SERVER_HOST = HOST
SERVER_PORT = PORT

# ============================================================================
# MODEL SETTINGS
# ============================================================================
MODEL_PATH = MODEL_DIR / "best.pt"
MODEL_PATH_SECONDARY = MODEL_DIR / "best1.pt"  # Secondary model for ensemble
USE_ENSEMBLE = False  # Enable ensemble detection (uses both models)
FALLBACK_MODEL = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.5

# Detection Classes
# Update these based on your trained model
DROWNING_CLASS_ID = 1  # Class ID for drowning detection
PERSON_CLASS_ID = 0    # Class ID for person detection

# ============================================================================
# PROCESSING SETTINGS
# ============================================================================
SKIP_FRAMES = 8 # Process every frame (matches video speed, most accurate)
JPEG_QUALITY = 90  # Higher quality for better visualization

# Motion Detection (Smart Frame Skipping)
USE_MOTION_DETECTION = True  # Enable motion-based frame skipping
MOTION_THRESHOLD = 1500      # Skip ML processing if motion score < threshold

# Legacy compatibility
FRAME_SKIP = SKIP_FRAMES
MAX_UPLOAD_SIZE_MB = 500  # Maximum video upload size

# ============================================================================
# DETECTION THRESHOLDS (in frames)
# ============================================================================
WARNING_THRESHOLD = 30  # Frames before WARNING state
DANGER_THRESHOLD = 60   # Frames before DANGER state

# Legacy compatibility (convert frames to seconds assuming 30 FPS)
WARNING_DURATION_SEC = WARNING_THRESHOLD / 30
DROWNING_DURATION_SEC = DANGER_THRESHOLD / 30

# ============================================================================
# TRACKING SETTINGS
# ============================================================================
MAX_TRACK_AGE = 60  # Frames before removing lost tracks

# Legacy DeepSORT compatibility
MAX_AGE = MAX_TRACK_AGE
N_INIT = 2                # Confirm tracks faster
MAX_COSINE_DISTANCE = 0.4 # Lenient appearance matching
NMS_MAX_OVERLAP = 0.7     # Reduce duplicate detections

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

# Email Configuration (SMTP)
# SMTP_USERNAME and SMTP_PASSWORD imported from credentials.py
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_FROM_EMAIL = ""  # Sender email (defaults to SMTP_USERNAME if empty)

# SMS/WhatsApp Configuration (Twilio)
# All Twilio credentials imported from credentials.py

# Recipients - imported from credentials.py
# NOTIFICATION_RECIPIENTS loaded from .env file

# ============================================================================
# POSE ESTIMATION SETTINGS (NEW - Pose-Driven Detection)
# ============================================================================
# Enable pose-driven behavior classification (set to False to use legacy heuristic)
USE_POSE_ESTIMATION = True

# Pose model configuration
POSE_MODEL_TYPE = "yolov8-pose"  # Options: "yolov8-pose", "mediapipe"
POSE_MODEL_PATH = MODEL_DIR / "yolov8n-pose.pt"  # Will auto-download if not found
POSE_CONFIDENCE_THRESHOLD = 0.3  # Minimum confidence for keypoints (0.0-1.0)

# Fallback behavior
FALLBACK_TO_HEURISTIC = True  # Use position-based detection if pose fails

# ============================================================================
# BEHAVIOR CLASSIFICATION SETTINGS (NEW)
# ============================================================================
# Temporal analysis window
TEMPORAL_WINDOW_SIZE = 90  # Frames to keep in sliding window (3 sec @ 30 FPS)
BEHAVIOR_UPDATE_INTERVAL = 1  # Classify behavior every N frames (1 = every frame)

# Behavior detection thresholds
THRASHING_THRESHOLD = 0.4  # Motion variance threshold for struggling detection
STILLNESS_THRESHOLD = 60  # Frames of minimal movement for drowning
VERTICAL_ORIENTATION_THRESHOLD = 60  # Degrees from horizontal for struggling

# Enhanced state transition thresholds (in frames)
ATTENTION_THRESHOLD = 15  # Frames before ATTENTION state (unusual behavior)
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
SECONDARY_POSE_RESIZE = 512  # Resize frames to 512px for faster inference
SECONDARY_POSE_FRAME_SKIP = 2  # Process every 2nd frame (1:2 skip ratio)

# LSTM temporal classifier
USE_LSTM_CLASSIFIER = True  # Enable LSTM-based risk classification
LSTM_MODEL_PATH = MODEL_DIR / "behavior" / "drowning_lstm.pt"
LSTM_BUFFER_SIZE = 90  # 3 seconds @ 30 FPS
LSTM_MIN_FRAMES = 30  # Minimum frames before inference (1 second)
LSTM_DEVICE = 'cpu'  # Force CPU for LSTM (lightweight model)

# Risk scoring
LSTM_DANGER_THRESHOLD = 0.7  # Danger probability threshold
LSTM_WARNING_THRESHOLD = 0.4  # Warning probability threshold

# ============================================================================

