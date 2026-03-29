# POOLGUARD - AI Based Drowning Detection System
## Presentation Document

---

## 1. Project Results
Testing results show that the system successfully detects swimmers and tracks their movements in real-time, identifying potential drowning situations within seconds. 

**Key results include:**
* **Accurate person detection** using YOLO model.
* **Continuous tracking** using DeepSORT algorithm to persist IDs and maintain state histories.
* **Real-time video analysis** drawing bounding boxes and pose skeletons directly over active camera feeds.
* **Detection of drowning behavior** based on positional analysis, LSTM predictions, and temporal frame windowing.
* **Immediate alert generation** sending high-priority notifications to mobile devices and web modules during danger situations.

---

## 2. System Architecture & Code Implementations

PoolGuard integrates a Python-based intelligent backend with a fast Flutter mobile application. Below are key components of the working architecture.

### A. Configuration & AI Thresholds (`config.py`)
This file organizes all neural network parameters and heuristic tunings cleanly.

```python
# config.py - Detection and AI thresholds
WARNING_THRESHOLD = 20  # Frames before WARNING state (~0.67s @ 30fps)
DANGER_THRESHOLD = 45   # Frames before DANGER state (~1.5s @ 30fps)
MAX_TRACK_AGE = 45      # Frames before removing lost tracks 

# New Pose-Driven Behavior Classification
USE_POSE_ESTIMATION = True
POSE_MODEL_TYPE = "yolov8-pose"
USE_LSTM_CLASSIFIER = True
LSTM_DANGER_THRESHOLD = 0.55  # Confidence required for purely LSTM alarm
```

### B. Core Backend API & Streaming (`app.py`)
The backend uses FastAPI to stream live processed video to web clients and handle HTTP requests seamlessly without blocking the AI process.

```python
# app.py - Video Streaming Endpoint
@app.get("/api/cameras/{camera_id}/mjpeg")
async def mjpeg_stream(camera_id: int, current_user: dict = Depends(get_current_user_from_query_token)):
    """
    MJPEG streaming proxy — pushes frames from the continuous AI process
    over HTTP. Lets WebViews display the live feed efficiently.
    """
    async def frame_generator():
        last_frame_no = -1
        while True:
            frame_data = BackgroundCameraManager.latest_frames.get(camera_id)
            if frame_data and frame_data.get('type') == 'frame':
                frame_no = frame_data.get('frame_number', -1)
                if frame_no != last_frame_no:
                    jpg_bytes = base64.b64decode(frame_data['analysis_frame'])
                    yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n")
                    last_frame_no = frame_no
            await asyncio.sleep(0.033)

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")
```

### C. Database Management (`database.py`)
Uses PostgreSQL with connection pooling. The `Alert` model handles the lifecycle of danger events.

```python
# database.py - Alert Lifecycle
class Alert:
    @staticmethod
    def create(track_id: int, alert_type: str, user_id: Optional[int] = None, camera_name: str = 'Main Camera') -> Optional[int]:
        query = """
            INSERT INTO alerts (user_id, track_id, alert_type, camera_name, escalated_to_admin)
            VALUES (%s, %s, %s, %s, FALSE) RETURNING id
        """
        return db.execute_query(query, (user_id, track_id, alert_type.lower(), camera_name), fetch=False)

    @staticmethod
    def resolve(alert_id: int, user_id: Optional[int] = None) -> bool:
        """Mark alert as resolved and record the user who did it"""
        query = "UPDATE alerts SET resolved_at = CURRENT_TIMESTAMP, user_id = %s WHERE id = %s"
        return db.execute_query(query, (user_id, alert_id), fetch=False)
```

### D. Mobile Guard Interface (`alert_detail_screen.dart`)
The Flutter mobile application allows on-duty lifeguards to receive alerts instantly and acknowledge them to clear the global queue.

```dart
// alert_detail_screen.dart - Acknowledge Action
Future<void> _acknowledge() async {
  setState(() => _acknowledging = true);

  final ok = await context
      .read<AlertProvider>()
      .acknowledgeAlert(widget.alert.alertId);

  if (!mounted) return;

  if (ok) {
    Navigator.pop(context); // Return to main dashboard once resolved
  } else {
    // Show error snackbar...
  }
}
```

---

## 3. Predicted Questions & Answers

**Q1: How does PoolGuard differentiate regular swimming from actual drowning?**
* **A:** Instead of just looking at vertical motion, the system combines temporal bounds (how long a person remains still or thrashing in a specific posture) with an advanced LSTM (Long Short-Term Memory) classifier that analyzes a sequence of points from a skeletal pose map over 45 frames. Regular swimming moves horizontally, whereas drowning often shows distinct vertical bobbing or lack of motion.

**Q2: Will the system trigger false alarms if someone is standing still in the shallow end?**
* **A:** We mitigated this by setting strict bounding box overlap and utilizing Pose Estimation. The pose estimation determines whether the body's orientation and depth indicate an impending drowning incident versus someone simply standing (where shoulders and head remain steady above water without thrashing signs).

**Q3: What happens if multiple people are in the pool and they cross paths?**
* **A:** We integrated the **DeepSORT** algorithm. By evaluating cosine distance of visual features and intersection-over-union (IOU) for bounding boxes, it maintains the distinct ID of an individual even if they get momentarily obscured by another swimmer.

**Q4: How does the app receive real-time alerts?**
* **A:** The system pushes alerts via Firebase Cloud Messaging (FCM) using a high-priority heads-up configuration. A background polling mechanism acts as an ultra-reliable fallback in case push notifications fail.

---

## 4. Difficulties Encountered

1. **Hardware Limitations for Real-Time Feeds:** It was challenging to run YOLO, Pose models, and an LSTM concurrently at 30 FPS. *Solution:* Utilized TensorRT/GPU acceleration, resized `YOLO_IMG_SIZE` to 640px, and skipped specific frames (`SKIP_FRAMES=2`) to boost temporal context without overloading the CPU.
2. **Push Notification Latency:** Ensuring mobile phones received critical alerts without iOS/Android battery management delaying them required configuring high-priority tokens.
3. **Ghost Inferences:** The pose model sometimes detected bodies in water reflections. *Solution:* We rebalanced `POSE_CONFIDENCE_THRESHOLD`.

---

## 5. Merits & Advantages

* **Unblinking Surveillance:** Functions tirelessly, immune to the visual fatigue that affects human lifeguards.
* **Rapid Deployment:** Can connect directly to existing pool RTSP/IP cameras without requiring specialized hardware installations underwater.
* **Full-Stack Ecosystem:** Supported by a robust PostgreSQL database, an Admin Dashboard, and a cross-platform mobile app.
* **Instant Collaboration:** When one lifeguard clicks "Acknowledge" on the mobile app, the alert resolves instantly across the entire system.

---

## 6. System Flaws & Limitations

* **Lighting Dependencies:** High surface glare or complete darkness negatively impacts the optical camera's ability to map pose skeletons perfectly. An IR-integrated hardware camera would be necessary for nighttime use.
* **Extreme Crowds:** In highly congested public wave-pools, the overlap of bodies reduces the accuracy of continuous DeepSORT tracking.
* **Submerged Bodies:** Standard RGB cameras struggle when bodies are deep underwater and visually refracted. The system relies heavily on detecting surface distress (the sequence leading up to drowning).
