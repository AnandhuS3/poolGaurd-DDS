# Pose-Driven Temporal Behavior Classification Pipeline - Refactoring Plan

**Date:** February 15, 2026  
**Version:** v4 → v5 (Pose-Driven)  
**Objective:** Replace heuristic time-based drowning detection with modular pose-driven temporal behavior classification

---

## 1. EXECUTIVE SUMMARY

### Current System (Heuristic-Based)
- **Detection Method:** Position-based (bottom 60% of frame)
- **Temporal Logic:** Simple frame counter (frames_underwater)
- **State Machine:** SAFE → WARNING → DANGER
- **Limitations:**
  - No pose analysis (can't distinguish diving from drowning)
  - No motion pattern recognition
  - False positives on intentional submersion
  - No body orientation analysis

### Proposed System (Pose-Driven)
- **Detection Method:** Pose keypoint analysis + temporal behavior patterns
- **Temporal Logic:** Multi-feature temporal classification
- **State Machine:** Enhanced with behavior context
- **Advantages:**
  - Distinguishes swimming, diving, floating, struggling
  - Analyzes body orientation and limb movement
  - Temporal pattern recognition (thrashing, stillness)
  - Contextual state transitions

---

## 2. ARCHITECTURE OVERVIEW

### 2.1 New Module Structure

```
core/
├── process_video.py          # MODIFIED: Integration layer
├── pose_estimation/          # NEW: Pose analysis module
│   ├── __init__.py
│   ├── pose_detector.py      # Pose estimation (YOLOv8-pose or MediaPipe)
│   ├── keypoint_analyzer.py  # Keypoint feature extraction
│   └── pose_features.py      # Feature definitions
├── behavior_classification/  # NEW: Behavior analysis module
│   ├── __init__.py
│   ├── temporal_buffer.py    # Sliding window for temporal features
│   ├── behavior_classifier.py # Rule-based + ML classifier
│   ├── behavior_patterns.py  # Pattern definitions
│   └── state_machine.py      # Enhanced state transitions
└── config.py                 # MODIFIED: Add pose/behavior configs
```

### 2.2 Data Flow

```
Video Frame
    ↓
YOLO Person Detection (existing)
    ↓
DeepSORT Tracking (existing)
    ↓
[NEW] Pose Estimation (per tracked person)
    ↓
[NEW] Keypoint Feature Extraction
    ↓
[NEW] Temporal Buffer (sliding window)
    ↓
[NEW] Behavior Classification
    ↓
[NEW] Enhanced State Machine
    ↓
WebSocket Output (existing)
```

---

## 3. DETAILED COMPONENT DESIGN

### 3.1 Pose Estimation Module

**File:** `core/pose_estimation/pose_detector.py`

**Responsibilities:**
- Extract 17 COCO keypoints per person
- Handle occlusions and low-confidence keypoints
- Normalize coordinates relative to bounding box

**Implementation Options:**
1. **YOLOv8-pose** (Recommended)
   - Pros: Fast, integrated with existing YOLO pipeline
   - Cons: Requires pose-trained model
2. **MediaPipe Pose** (Alternative)
   - Pros: Pre-trained, robust
   - Cons: Slower, separate inference

**Keypoints (COCO format):**
```
0: nose, 1-2: eyes, 3-4: ears, 5-6: shoulders,
7-8: elbows, 9-10: wrists, 11-12: hips,
13-14: knees, 15-16: ankles
```

### 3.2 Keypoint Analyzer

**File:** `core/pose_estimation/keypoint_analyzer.py`

**Features Extracted:**
1. **Body Orientation:**
   - Vertical angle (upright vs horizontal)
   - Face-up vs face-down (shoulder-hip alignment)
   
2. **Limb Positions:**
   - Arms above/below water (relative to shoulders)
   - Legs spread/together
   - Limb extension ratio

3. **Motion Patterns:**
   - Keypoint velocity (frame-to-frame displacement)
   - Acceleration (change in velocity)
   - Thrashing score (high-frequency limb movement)

4. **Stability Metrics:**
   - Center of mass movement
   - Pose consistency (keypoint variance)
   - Stillness duration

### 3.3 Temporal Buffer

**File:** `core/behavior_classification/temporal_buffer.py`

**Design:**
- Sliding window: 90 frames (3 seconds @ 30 FPS)
- Stores per-person feature history
- Computes temporal statistics:
  - Mean, std, min, max
  - Trend analysis (increasing/decreasing)
  - Pattern detection (periodic, erratic, stable)

**Data Structure:**
```python
{
    track_id: {
        "features": deque(maxlen=90),  # Feature vectors
        "timestamps": deque(maxlen=90), # Frame numbers
        "statistics": {
            "mean_orientation": float,
            "motion_variance": float,
            "thrashing_frequency": float,
            "stillness_duration": int
        }
    }
}
```

### 3.4 Behavior Classifier

**File:** `core/behavior_classification/behavior_classifier.py`

**Behavior Categories:**
1. **SWIMMING** - Coordinated limb movement, horizontal orientation
2. **DIVING** - Intentional submersion, streamlined pose
3. **FLOATING** - Minimal movement, stable position
4. **STRUGGLING** - Erratic movement, vertical orientation, thrashing
5. **DROWNING** - Minimal movement, submerged, face-down

**Classification Logic:**
```python
def classify_behavior(pose_features, temporal_stats):
    # Rule-based decision tree
    if temporal_stats["stillness_duration"] > 60:
        if pose_features["depth_ratio"] > 0.7:
            return "DROWNING"
        return "FLOATING"
    
    if temporal_stats["thrashing_frequency"] > 0.5:
        if pose_features["orientation"] > 60:  # Vertical
            return "STRUGGLING"
    
    if pose_features["limb_coordination"] > 0.7:
        return "SWIMMING"
    
    if pose_features["streamlined_score"] > 0.8:
        return "DIVING"
    
    return "UNKNOWN"
```

### 3.5 Enhanced State Machine

**File:** `core/behavior_classification/state_machine.py`

**States:**
- **SAFE** - Normal swimming/floating
- **ATTENTION** - Unusual behavior (new state)
- **WARNING** - Struggling detected
- **DANGER** - Drowning detected

**Transition Rules:**
```
SAFE → ATTENTION: Behavior changes to STRUGGLING
ATTENTION → WARNING: STRUGGLING for 30 frames (1 sec)
WARNING → DANGER: DROWNING behavior for 60 frames (2 sec)
DANGER → WARNING: Behavior improves (requires manual review)
WARNING → SAFE: Normal behavior for 45 frames (1.5 sec)
ATTENTION → SAFE: Normal behavior for 30 frames (1 sec)
```

**Key Difference from Current:**
- Context-aware transitions (not just position-based)
- Behavior history influences transitions
- Requires sustained abnormal behavior (reduces false positives)

---

## 4. CONFIGURATION CHANGES

### 4.1 New Config Parameters

**File:** `core/config.py`

```python
# ============================================================================
# POSE ESTIMATION SETTINGS
# ============================================================================
USE_POSE_ESTIMATION = True  # Enable pose-driven detection
POSE_MODEL_TYPE = "yolov8-pose"  # Options: "yolov8-pose", "mediapipe"
POSE_MODEL_PATH = MODEL_DIR / "yolov8n-pose.pt"
POSE_CONFIDENCE_THRESHOLD = 0.3  # Min confidence for keypoints

# ============================================================================
# BEHAVIOR CLASSIFICATION SETTINGS
# ============================================================================
TEMPORAL_WINDOW_SIZE = 90  # Frames (3 seconds @ 30 FPS)
BEHAVIOR_UPDATE_INTERVAL = 5  # Classify every N frames

# Behavior thresholds
THRASHING_THRESHOLD = 0.5  # Motion variance threshold
STILLNESS_THRESHOLD = 60  # Frames of minimal movement
VERTICAL_ORIENTATION_THRESHOLD = 60  # Degrees from horizontal

# State transition thresholds (in frames)
ATTENTION_THRESHOLD = 15  # Unusual behavior
WARNING_THRESHOLD = 30   # Struggling
DANGER_THRESHOLD = 60    # Drowning

# ============================================================================
# LEGACY COMPATIBILITY
# ============================================================================
FALLBACK_TO_HEURISTIC = True  # Use position-based if pose fails
```

---

## 5. IMPLEMENTATION PHASES

### Phase 1: Foundation (Week 1)
**Goal:** Set up pose estimation infrastructure

**Tasks:**
1. Create module structure (`pose_estimation/`, `behavior_classification/`)
2. Implement `pose_detector.py` with YOLOv8-pose
3. Implement `keypoint_analyzer.py` with basic features
4. Add unit tests for pose extraction
5. Update `config.py` with new parameters

**Deliverables:**
- Pose keypoints extracted per person
- Basic feature computation (orientation, limb positions)
- Fallback to heuristic if pose fails

### Phase 2: Temporal Analysis (Week 2)
**Goal:** Build temporal feature extraction

**Tasks:**
1. Implement `temporal_buffer.py` with sliding window
2. Add temporal statistics computation
3. Implement motion pattern detection
4. Add visualization for temporal features (debug mode)
5. Integration with existing tracking

**Deliverables:**
- Temporal features computed over 90-frame window
- Motion patterns detected (thrashing, stillness)
- Debug visualization showing feature trends

### Phase 3: Behavior Classification (Week 3)
**Goal:** Implement behavior classifier

**Tasks:**
1. Implement `behavior_classifier.py` with rule-based logic
2. Define behavior patterns in `behavior_patterns.py`
3. Implement `state_machine.py` with enhanced transitions
4. Add behavior labels to WebSocket output
5. Update frontend to display behavior (optional)

**Deliverables:**
- Behavior classification (SWIMMING, DIVING, etc.)
- Enhanced state machine with context
- Behavior labels in UI

### Phase 4: Integration & Testing (Week 4)
**Goal:** Full integration and validation

**Tasks:**
1. Modify `process_video.py` to use new pipeline
2. Preserve existing FastAPI routes and WebSocket
3. Add configuration toggle (pose vs heuristic)
4. Comprehensive testing with real videos
5. Performance optimization

**Deliverables:**
- Fully integrated pose-driven pipeline
- Backward compatibility maintained
- Performance benchmarks
- Documentation updated

---

## 6. BACKWARD COMPATIBILITY STRATEGY

### 6.1 Dual-Mode Operation

```python
# In process_video.py
if USE_POSE_ESTIMATION and pose_available:
    # New pose-driven pipeline
    behavior = classify_behavior(pose_features, temporal_stats)
    state = state_machine.update(behavior)
else:
    # Fallback to existing heuristic
    state = legacy_position_based_detection(person_data)
```

### 6.2 Preserved Interfaces

**No changes to:**
- FastAPI routes (`/analyze/upload`, `/analyze/youtube`, etc.)
- WebSocket protocol (same JSON structure)
- Database schema
- Authentication/authorization
- Notification system

**Optional additions:**
- New WebSocket field: `"behavior": "SWIMMING"` (backward compatible)
- New config toggles (default to legacy behavior)

---

## 7. TESTING STRATEGY

### 7.1 Unit Tests

**New test files:**
- `tests/test_pose_detector.py` - Pose extraction accuracy
- `tests/test_keypoint_analyzer.py` - Feature computation
- `tests/test_temporal_buffer.py` - Sliding window logic
- `tests/test_behavior_classifier.py` - Classification rules
- `tests/test_state_machine.py` - State transitions

### 7.2 Integration Tests

**Scenarios:**
1. **Swimming video** - Should classify as SAFE/SWIMMING
2. **Diving video** - Should not trigger DANGER
3. **Drowning simulation** - Should trigger WARNING → DANGER
4. **Pose estimation failure** - Should fallback to heuristic
5. **High-speed video** - Should handle FPS variations

### 7.3 Performance Benchmarks

**Metrics:**
- FPS with pose estimation (target: >15 FPS on CPU)
- Latency added by pose pipeline (target: <50ms)
- Memory usage (target: <2GB)
- False positive rate (target: <5%)
- False negative rate (target: <1%)

---

## 8. RISK MITIGATION

### 8.1 Technical Risks

**Risk 1: Pose estimation too slow**
- **Mitigation:** Process pose every N frames (BEHAVIOR_UPDATE_INTERVAL)
- **Fallback:** Use heuristic if latency exceeds threshold

**Risk 2: Pose model not available**
- **Mitigation:** Download on first run, cache locally
- **Fallback:** Graceful degradation to heuristic

**Risk 3: Occlusions break pose tracking**
- **Mitigation:** Interpolate missing keypoints, use temporal smoothing
- **Fallback:** Skip pose analysis for occluded frames

### 8.2 Deployment Risks

**Risk 1: Breaking existing deployments**
- **Mitigation:** Feature flag (USE_POSE_ESTIMATION=False by default)
- **Rollback:** Keep legacy code path intact

**Risk 2: Model download failures**
- **Mitigation:** Include model in repository (if license allows)
- **Alternative:** Provide manual download instructions

---

## 9. SUCCESS CRITERIA

### 9.1 Functional Requirements
- ✅ Pose keypoints extracted for all tracked persons
- ✅ Behavior classification accurate (>90% on test set)
- ✅ State transitions context-aware
- ✅ False positive rate reduced by >50%
- ✅ All existing features preserved

### 9.2 Performance Requirements
- ✅ Processing speed: >15 FPS on CPU, >30 FPS on GPU
- ✅ Latency: <100ms added per frame
- ✅ Memory: <2GB total usage

### 9.3 Compatibility Requirements
- ✅ No changes to API contracts
- ✅ No database schema changes
- ✅ Existing YOLO weights still work
- ✅ WebSocket protocol unchanged

---

## 10. NEXT STEPS

### Immediate Actions (Today)
1. Review and approve this plan
2. Set up development branch (`feature/pose-driven-detection`)
3. Download YOLOv8-pose model
4. Create module structure

### Week 1 Milestones
- [ ] Pose estimation working
- [ ] Basic features extracted
- [ ] Unit tests passing

### Week 2 Milestones
- [ ] Temporal buffer implemented
- [ ] Motion patterns detected
- [ ] Integration tests passing

### Week 3 Milestones
- [ ] Behavior classifier working
- [ ] State machine enhanced
- [ ] Frontend updated

### Week 4 Milestones
- [ ] Full integration complete
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Ready for production testing

---

## 11. APPENDIX: TECHNICAL REFERENCES

### Pose Estimation Models
- **YOLOv8-pose:** https://docs.ultralytics.com/tasks/pose/
- **MediaPipe Pose:** https://google.github.io/mediapipe/solutions/pose.html

### Behavior Classification Research
- Drowning detection using pose estimation (IEEE papers)
- Human activity recognition in videos
- Temporal action detection methods

### Code Examples
- YOLOv8-pose inference: See `examples/pose_inference.py` (to be created)
- Temporal buffer: See `examples/temporal_analysis.py` (to be created)

---

**End of Refactoring Plan**
