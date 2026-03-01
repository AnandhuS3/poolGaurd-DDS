# System Architecture Diagram - Complete Integration

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     DDS v5.1 - Complete System                          │
│                  Pose-Driven + LSTM Integration                         │
└─────────────────────────────────────────────────────────────────────────┘

                              INPUT
                                ↓
                    ┌───────────────────────┐
                    │   Video Stream        │
                    │   (30 FPS, 1920x1080) │
                    └───────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      EXISTING PIPELINE (Preserved)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐        │
│   │ YOLO Person  │  →   │  DeepSORT    │  →   │   Track      │        │
│   │  Detection   │      │   Tracking   │      │  Management  │        │
│   └──────────────┘      └──────────────┘      └──────────────┘        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
                    ┌───────────────────────┐
                    │   Confirmed Tracks    │
                    │   (ID, BBox, Class)   │
                    └───────────────────────┘
                                ↓
        ┌───────────────────────┴───────────────────────┐
        │                                               │
        ↓                                               ↓
┌───────────────────────┐                   ┌───────────────────────┐
│   PRIMARY PIPELINE    │                   │  SECONDARY PIPELINE   │
│   (Phase 1 - NEW)     │                   │  (Phase 2 - NEW)      │
│   Every Frame         │                   │  Every 2nd Frame      │
└───────────────────────┘                   └───────────────────────┘
        ↓                                               ↓
┌───────────────────────┐                   ┌───────────────────────┐
│  YOLOv8-pose          │                   │  Resize Frame         │
│  Full Resolution      │                   │  1920x1080 → 512x512  │
│  GPU/CPU              │                   └───────────────────────┘
└───────────────────────┘                               ↓
        ↓                                   ┌───────────────────────┐
┌───────────────────────┐                   │  YOLOv8n-pose         │
│  17 COCO Keypoints    │                   │  CPU-only             │
│  per Person           │                   │  Lightweight          │
└───────────────────────┘                   └───────────────────────┘
        ↓                                               ↓
┌───────────────────────┐                   ┌───────────────────────┐
│  Keypoint Analyzer    │                   │  Feature Extractor    │
│  - Orientation        │                   │  4 Features:          │
│  - Limb positions     │                   │  1. vertical_ratio    │
│  - Motion patterns    │                   │  2. arm_velocity      │
│  - Stability          │                   │  3. horizontal_disp   │
└───────────────────────┘                   │  4. head_oscillation  │
        ↓                                   └───────────────────────┘
┌───────────────────────┐                               ↓
│  Temporal Buffer      │                   ┌───────────────────────┐
│  90 frames (3 sec)    │                   │  Rolling Buffer       │
│  Per-track history    │                   │  90 frames (3 sec)    │
└───────────────────────┘                   │  Per-track features   │
        ↓                                   └───────────────────────┘
┌───────────────────────┐                               ↓
│  Behavior Classifier  │                   ┌───────────────────────┐
│  Rule-based:          │                   │  LSTM Classifier      │
│  - SWIMMING           │                   │  Input: (90, 4)       │
│  - DIVING             │                   │  Hidden: 32 units     │
│  - FLOATING           │                   │  Output: 3 classes    │
│  - STRUGGLING         │                   └───────────────────────┘
│  - DROWNING           │                               ↓
└───────────────────────┘                   ┌───────────────────────┐
        ↓                                   │  Softmax Scores       │
┌───────────────────────┐                   │  [P(SAFE),            │
│  Enhanced State       │                   │   P(WARNING),         │
│  Machine:             │                   │   P(DANGER)]          │
│  - SAFE               │                   └───────────────────────┘
│  - ATTENTION (new)    │                               ↓
│  - WARNING            │                   ┌───────────────────────┐
│  - DANGER             │                   │  Risk State           │
└───────────────────────┘                   │  SAFE/WARNING/DANGER  │
        ↓                                   └───────────────────────┘
        │                                               │
        └───────────────────────┬───────────────────────┘
                                ↓
                    ┌───────────────────────┐
                    │  Heuristic Fallback   │
                    │  (if pose fails)      │
                    │  Position-based       │
                    └───────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         COMBINED OUTPUT                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Person Data (per track):                                              │
│   ┌────────────────────────────────────────────────────────────┐       │
│   │  Existing:                                                  │       │
│   │  - id, bbox, state, alert, confidence                       │       │
│   │                                                             │       │
│   │  Pose-Driven (NEW):                                         │       │
│   │  - behavior: "swimming" | "diving" | ...                    │       │
│   │  - pose_available: true/false                               │       │
│   │                                                             │       │
│   │  LSTM Risk (NEW):                                           │       │
│   │  - lstm_risk_state: "SAFE" | "WARNING" | "DANGER"          │       │
│   │  - lstm_risk_scores: [0.92, 0.06, 0.02]                    │       │
│   │  - lstm_confidence: 0.92                                    │       │
│   │  - lstm_available: true/false                               │       │
│   └────────────────────────────────────────────────────────────┘       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                ↓
                    ┌───────────────────────┐
                    │  WebSocket Stream     │
                    │  JSON Messages        │
                    │  (Backward Compatible)│
                    └───────────────────────┘
                                ↓
                    ┌───────────────────────┐
                    │  Frontend Display     │
                    │  + Notifications      │
                    └───────────────────────┘
```

## Data Flow Timeline

```
Frame 0 (t=0ms):
├─ YOLO Detection: 50ms
├─ DeepSORT Tracking: 10ms
├─ Primary Pose (YOLOv8-pose): 40ms
├─ Keypoint Analysis: 5ms
├─ Behavior Classification: 3ms
├─ Secondary Pose (512px): 30ms
├─ LSTM Feature Extract: 2ms
├─ LSTM Inference: 3ms
└─ Total: ~143ms (7 FPS) on CPU

Frame 1 (t=33ms):
├─ YOLO Detection: 50ms
├─ DeepSORT Tracking: 10ms
├─ Primary Pose: 40ms
├─ Keypoint Analysis: 5ms
├─ Behavior Classification: 3ms
├─ Secondary Pose: SKIPPED (frame skip)
├─ LSTM: SKIPPED
└─ Total: ~108ms (9 FPS) on CPU

Frame 2 (t=66ms):
├─ YOLO Detection: 50ms
├─ DeepSORT Tracking: 10ms
├─ Primary Pose: 40ms
├─ Keypoint Analysis: 5ms
├─ Behavior Classification: 3ms
├─ Secondary Pose: 30ms
├─ LSTM: 5ms
└─ Total: ~143ms (7 FPS) on CPU

Average: ~125ms per frame = 8 FPS on CPU
With GPU: ~30ms per frame = 33 FPS
```

## Module Dependencies

```
core/
├── process_video.py (MAIN ORCHESTRATOR)
│   ├── Uses: YOLO, DeepSORT (existing)
│   ├── Uses: pose_driven_processor (Phase 1)
│   └── Uses: behavior.inference (Phase 2)
│
├── pose_driven_processor.py (Phase 1 Wrapper)
│   ├── Uses: pose_estimation.pose_detector
│   ├── Uses: pose_estimation.keypoint_analyzer
│   ├── Uses: behavior_classification.temporal_buffer
│   ├── Uses: behavior_classification.behavior_classifier
│   └── Uses: behavior_classification.state_machine
│
├── pose_estimation/ (Phase 1)
│   ├── pose_detector.py
│   │   └── Uses: ultralytics.YOLO or mediapipe
│   ├── keypoint_analyzer.py
│   └── pose_features.py
│
├── behavior_classification/ (Phase 1)
│   ├── temporal_buffer.py
│   ├── behavior_classifier.py
│   ├── behavior_patterns.py
│   └── state_machine.py
│
└── behavior/ (Phase 2)
    ├── inference.py (LSTM Orchestrator)
    │   ├── Uses: behavior_features.BehaviorFeatureExtractor
    │   └── Uses: temporal_model.TemporalLSTMClassifier
    ├── behavior_features.py
    └── temporal_model.py
        └── Uses: torch.nn
```

## Configuration Flow

```
core/config.py
├── USE_POSE_ESTIMATION = True
│   ├── Enables: Primary pose-driven pipeline
│   ├── Model: POSE_MODEL_PATH (yolov8n-pose.pt)
│   └── Fallback: FALLBACK_TO_HEURISTIC
│
├── USE_SECONDARY_POSE = True
│   ├── Enables: Secondary pose for LSTM
│   ├── Model: SECONDARY_POSE_MODEL_PATH
│   ├── Optimization: SECONDARY_POSE_RESIZE = 512
│   └── Optimization: SECONDARY_POSE_FRAME_SKIP = 2
│
└── USE_LSTM_CLASSIFIER = True
    ├── Enables: LSTM risk inference
    ├── Model: LSTM_MODEL_PATH (drowning_lstm.pt)
    ├── Buffer: LSTM_BUFFER_SIZE = 90
    └── Device: LSTM_DEVICE = 'cpu'
```

## State Transitions

```
Person State Machine (Enhanced):

SAFE (Green)
  ↓ 15 frames of unusual behavior
ATTENTION (Yellow) ← NEW STATE
  ↓ 30 frames of struggling
WARNING (Orange)
  ↓ 60 frames of drowning behavior
DANGER (Red) ← STICKY STATE

Recovery paths:
ATTENTION → SAFE: 30 frames normal
WARNING → SAFE: 45 frames normal
DANGER → WARNING: Manual review required
```

## Risk Scoring Logic

```
Combined Risk Assessment:

1. Pose-Driven Behavior:
   ├─ SWIMMING → Low risk
   ├─ DIVING → Low risk (intentional)
   ├─ FLOATING → Medium risk
   ├─ STRUGGLING → High risk
   └─ DROWNING → Critical risk

2. LSTM Risk Scores:
   ├─ P(SAFE) > 0.8 → Low risk
   ├─ P(WARNING) > 0.4 → Medium risk
   └─ P(DANGER) > 0.7 → High risk

3. Heuristic Fallback:
   ├─ Position < 60% → Low risk
   ├─ Position > 60%, <30 frames → Medium risk
   └─ Position > 60%, >60 frames → High risk

Final State = MAX(Pose-Driven, LSTM, Heuristic)
(Safety first: escalate, never de-escalate)
```

## Memory Layout (Per Track)

```
Track ID: 1
├── person_data (dict)
│   ├── state: "SAFE"
│   ├── behavior: "swimming"
│   ├── pose_available: true
│   ├── lstm_risk_state: "SAFE"
│   ├── lstm_risk_scores: [0.92, 0.06, 0.02]
│   └── ... (other fields)
│
├── pose_driven_processor
│   └── temporal_buffer (90 frames)
│       ├── PoseFeatures × 90
│       └── ~100KB
│
└── lstm_inference_engine
    └── track_buffer (90 frames)
        ├── keypoints (17, 3) × 90
        ├── features (4,) × 90
        └── ~100KB

Total per track: ~200KB
Total for 10 tracks: ~2MB
```

---

**Last Updated:** February 15, 2026  
**Version:** v5.1 (Complete Integration)  
**Status:** ✅ PRODUCTION READY
