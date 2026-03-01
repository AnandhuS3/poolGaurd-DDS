# System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT (Web Browser)                        │
│                         http://localhost:8000                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Video Upload │  │ YouTube URL  │  │   Control Buttons      │  │
│  │    Input     │  │    Input     │  │  Start │ Stop │ Reset  │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────────────────┘  │
│         │                  │                                        │
│         └──────────────────┴────────────┐                          │
│                                          ▼                          │
│                                   ┌──────────┐                      │
│                                   │  Upload  │                      │
│                                   │ Handler  │                      │
│                                   └─────┬────┘                      │
│                                         │                           │
│  ┌──────────────────────────────────────┼──────────────────────┐  │
│  │           WebSocket Connection       │                       │  │
│  │              ws://localhost:8000/ws/process                  │  │
│  └──────────────────────────────────────┼──────────────────────┘  │
│                                          ▼                          │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    HTML5 Canvas                             │   │
│  │        [Live Video Display with Bounding Boxes]            │   │
│  │                                                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                │   │
│  │  │ Person 1 │  │ Person 2 │  │ Person 3 │                │   │
│  │  │  ID: 1   │  │  ID: 2   │  │  ID: 3   │                │   │
│  │  │  SAFE🟢  │  │WARNING🟠 │  │ DANGER🔴 │                │   │
│  │  └──────────┘  └──────────┘  └──────────┘                │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────┐  ┌──────────────────────────────────┐   │
│  │   Statistics Panel  │  │       Event Log                  │   │
│  │  ┌────────────────┐ │  │  • 12:30 - Processing started   │   │
│  │  │ Persons: 3     │ │  │  • 12:31 - Person #1 detected   │   │
│  │  │ Alerts: 1      │ │  │  • 12:32 - ⚠️ DROWNING ALERT!   │   │
│  │  └────────────────┘ │  │  • 12:33 - Frame 450/1200       │   │
│  └─────────────────────┘  └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                   ▲ │
                    WebSocket      │ │  HTTP
                    (Frame Data)   │ │  (Upload)
                                   │ ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND SERVER (FastAPI)                        │
│                         app.py on Port 8000                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────┐         ┌──────────────────────┐          │
│  │  HTTP Endpoints    │         │  WebSocket Handler   │          │
│  │                    │         │                      │          │
│  │  POST /analyze/    │         │  /ws/process         │          │
│  │       upload       │         │                      │          │
│  │                    │         │  • Accept connection │          │
│  │  POST /analyze/    │         │  • Receive video path│          │
│  │       youtube      │         │  • Stream frames     │          │
│  │                    │         │  • Send tracking data│          │
│  │  GET /download/    │         └──────────┬───────────┘          │
│  │      {file}        │                    │                       │
│  └────────────────────┘                    │                       │
│                                             ▼                       │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │            Video Processing Pipeline                     │     │
│  │            (process_video.py)                            │     │
│  │                                                          │     │
│  │  1. Open Video ──────────────────────────────────────┐  │     │
│  │     (OpenCV VideoCapture)                            │  │     │
│  │                                                       ▼  │     │
│  │  2. Read Frame ──────────────────────────────────────┐  │     │
│  │                                                       │  │     │
│  │                                                       ▼  │     │
│  │  3. YOLO Detection ┌──────────────────────────────┐  │  │     │
│  │     ┌──────────────┤  best.pt Model               │  │  │     │
│  │     │              │  (Trained on drowning data)  │  │  │     │
│  │     │              └──────────────────────────────┘  │  │     │
│  │     │ Output: Bounding boxes, confidence, classes   │  │     │
│  │     │                                                │  │     │
│  │     ▼                                                │  │     │
│  │  4. DeepSORT Tracking                               │  │     │
│  │     ┌───────────────────────────────────────────┐   │  │     │
│  │     │ • Assign unique IDs                       │   │  │     │
│  │     │ • Track across frames                     │   │  │     │
│  │     │ • Handle occlusions                       │   │  │     │
│  │     │ • Maintain consistency                    │   │  │     │
│  │     └───────────────────────────────────────────┘   │  │     │
│  │                                                      │  │     │
│  │                                                      ▼  │     │
│  │  5. Drowning Detection Logic                         │  │     │
│  │     ┌───────────────────────────────────────────┐   │  │     │
│  │     │ IF class == DROWNING_CLASS_ID:            │   │  │     │
│  │     │   Start timer                             │   │  │     │
│  │     │   IF timer > 5 seconds:                   │   │  │     │
│  │     │     Status = DANGER                       │   │  │     │
│  │     │     Trigger Alert                         │   │  │     │
│  │     │   ELSE:                                   │   │  │     │
│  │     │     Status = WARNING                      │   │  │     │
│  │     │ ELSE:                                     │   │  │     │
│  │     │   Status = SAFE                           │   │  │     │
│  │     │   Reset timer                             │   │  │     │
│  │     └───────────────────────────────────────────┘   │  │     │
│  │                                                      │  │     │
│  │                                                      ▼  │     │
│  │  6. Draw Annotations                                 │  │     │
│  │     • Bounding boxes (color-coded)                   │  │     │
│  │     • Person IDs                                     │  │     │
│  │     • Status labels                                  │  │     │
│  │     • Frame info                                     │  │     │
│  │                                                      │  │     │
│  │                                                      ▼  │     │
│  │  7. Encode Frame                                     │  │     │
│  │     • Convert to JPEG                                │  │     │
│  │     • Base64 encode                                  │  │     │
│  │     • Package with metadata                          │  │     │
│  │                                                      │  │     │
│  │                                                      ▼  │     │
│  │  8. Send via WebSocket ──────────────────────────────┘  │     │
│  │     {                                                   │     │
│  │       "type": "frame",                                  │     │
│  │       "frame": "base64_data",                           │     │
│  │       "persons": [{id, bbox, status}],                  │     │
│  │       "summary": {total, alerts}                        │     │
│  │     }                                                   │     │
│  │                                                          │     │
│  │  9. Repeat for all frames ───────────────────────────┐  │     │
│  │                                                       │  │     │
│  │  10. Send completion message                         │  │     │
│  └──────────────────────────────────────────────────────┴──┘     │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                    File System                             │   │
│  │                                                            │   │
│  │  uploads/          output/           best.pt              │   │
│  │  • video1.mp4      • annotated_      [YOLO Model]         │   │
│  │  • video2.mp4        video1.mp4                           │   │
│  │  (temporary)       (optional)                              │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      CONFIGURATION LAYER                            │
│                          config.py                                  │
├─────────────────────────────────────────────────────────────────────┤
│  • SERVER_HOST, SERVER_PORT                                         │
│  • MODEL_PATH, CONFIDENCE_THRESHOLD                                 │
│  • DROWNING_CLASS_ID, DROWNING_DURATION_SEC                         │
│  • MAX_AGE, N_INIT, MAX_COSINE_DISTANCE                            │
│  • JPEG_QUALITY, COLOR_SAFE, COLOR_WARNING, COLOR_DANGER           │
└─────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════
                          DATA FLOW LEGEND
═══════════════════════════════════════════════════════════════════════

HTTP Request  ────────►  File Upload, Video Download
WebSocket     ═══════►  Bi-directional Real-time Communication
Frame Data    ········►  Base64 Encoded JPEG + Metadata
Processing    ▼▼▼▼▼▼►  Sequential Pipeline Operations

═══════════════════════════════════════════════════════════════════════
                        STATUS COLOR CODING
═══════════════════════════════════════════════════════════════════════

🟢 GREEN (SAFE)     - Person detected, no drowning behavior
🟠 ORANGE (WARNING) - Potential drowning detected, monitoring
🔴 RED (DANGER)     - Drowning alert! (sustained >5 seconds)

═══════════════════════════════════════════════════════════════════════
```

## Component Details

### Frontend Components:

1. **Video Canvas** - HTML5 canvas for displaying processed video
2. **Upload Interface** - File input and YouTube URL field
3. **WebSocket Client** - Maintains connection to server
4. **Statistics Dashboard** - Real-time person count and alerts
5. **Event Logger** - Timestamped event history
6. **Control Panel** - Start/Stop/Reset buttons

### Backend Components:

1. **FastAPI Server** - HTTP and WebSocket server
2. **Upload Handler** - Saves videos to uploads/
3. **WebSocket Handler** - Manages real-time connections
4. **Video Processor** - Frame-by-frame analysis
5. **YOLO Detector** - Object detection from best.pt
6. **DeepSORT Tracker** - Multi-object tracking
7. **Drowning Logic** - Time-based alert system

### Processing Pipeline:

1. Video frame extraction
2. YOLO object detection
3. DeepSORT person tracking
4. Drowning behavior analysis
5. Visual annotation
6. JPEG encoding
7. WebSocket transmission
8. Canvas rendering

### Data Models:

```json
{
  "person": {
    "id": "unique_track_id",
    "bbox": [x1, y1, x2, y2],
    "status": "safe|warning|danger",
    "alert": true/false,
    "class": 0/1
  },
  "summary": {
    "total": 3,
    "safe": 2,
    "warning": 0,
    "danger": 1,
    "alerts": 1
  }
}
```
