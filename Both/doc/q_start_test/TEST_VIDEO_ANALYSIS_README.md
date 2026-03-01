# Video Analysis Test - Usage Guide

## Overview

This test program analyzes a video file and displays real-time:
- **Person detection** (bounding boxes)
- **Pose estimation** (17 keypoints)
- **LSTM risk inference** (SAFE/WARNING/DANGER)
- **Risk probability bars** (visual confidence scores)
- **Processing statistics** (FPS, detections, etc.)

## Quick Start

### 1. Prepare a Test Video

Place a video file in the project directory, or use any video path:
```bash
# Example video locations
test_video.mp4           # In project root
videos/pool_video.mp4    # In videos folder
C:/path/to/video.mp4     # Absolute path
```

### 2. Run the Analysis

**Basic usage:**
```bash
python test_video_analysis.py --video test_video.mp4
```

**With custom output:**
```bash
python test_video_analysis.py --video test_video.mp4 --output result.mp4
```

**Headless mode (no display window):**
```bash
python test_video_analysis.py --video test_video.mp4 --no-display
```

**No output file (display only):**
```bash
python test_video_analysis.py --video test_video.mp4 --no-save
```

## Command Line Options

```
--video PATH        Input video file path (default: test_video.mp4)
--output PATH       Output video file path (default: output_analysis.mp4)
--no-display        Disable live preview window
--no-save           Don't save annotated output video
```

## Controls

While the video is playing:
- **`q`** - Quit analysis
- **`p`** - Pause/Resume playback

## Output

### Live Display Window

Shows real-time analysis with:
- **Green boxes** = SAFE risk level
- **Orange boxes** = WARNING risk level  
- **Red boxes** = DANGER risk level
- **Risk probability bars** below each person
- **Frame info** (top-left corner)
- **Statistics** (detections, poses, LSTM inferences)
- **Legend** (top-right corner)

### Saved Video

The annotated video is saved to `output_analysis.mp4` (or your specified path) with all visualizations.

### Console Output

```
======================================================================
Video Analysis - Pose-Driven + LSTM Risk Inference
======================================================================

1. Initializing models...
   ✅ Detection model loaded: weights/best.pt
   ✅ Pose detector loaded: weights/behavior/yolov8n-pose.pt
   ✅ LSTM engine loaded: weights/behavior/drowning_lstm.pt

2. Opening video: test_video.mp4
   ✅ Video opened successfully
   - Resolution: 1920x1080
   - FPS: 30
   - Total frames: 900
   - Duration: 30.0 seconds

3. Output will be saved to: output_analysis.mp4

4. Processing video...
   Progress: 10.0% (90/900) - FPS: 8.5
   Progress: 20.0% (180/900) - FPS: 8.7
   ...

======================================================================
Analysis Complete!
======================================================================

Processing Statistics:
  Total frames processed: 900
  Total person detections: 450
  Successful pose detections: 420
  LSTM inferences: 210

Risk Distribution:
  SAFE frames: 380
  WARNING frames: 35
  DANGER frames: 5

Performance:
  Total time: 105.3 seconds
  Average FPS: 8.5

✅ Output saved to: output_analysis.mp4
```

## What You'll See

### Person Detection
- Bounding boxes around detected persons
- Person ID labels
- Color-coded by risk level

### Risk Assessment
- **Risk State**: SAFE / WARNING / DANGER
- **Confidence**: 0.00 - 1.00
- **Buffer Status**: X/90 frames (needs 30+ for inference)

### Risk Probability Bars
Three bars showing probabilities:
- **SAFE** (green) - Normal swimming/floating
- **WARN** (orange) - Struggling/distress
- **DNGR** (red) - Drowning behavior

### Frame Information
- Current frame / Total frames
- Processing FPS
- Detection count
- Pose detection count
- LSTM inference count

## Troubleshooting

### Video Not Found
```
❌ Video not found: test_video.mp4
Please provide a valid video path
```
**Solution:** Provide correct video path with `--video` argument

### Low FPS (< 5 FPS)
**Causes:**
- Large video resolution
- CPU-only processing
- Multiple people in frame

**Solutions:**
1. Use smaller resolution video
2. Increase `FRAME_SKIP` in the script (line 21)
3. Reduce `RESIZE_FOR_POSE` (line 22)

### No Pose Detected
**Causes:**
- Person too small in frame
- Occlusion
- Poor lighting

**Check:**
- Person bounding box is large enough
- Person is clearly visible
- Confidence threshold (line 23)

### LSTM Always Shows SAFE
**Expected behavior** with dummy model. The dummy model is biased towards SAFE for safety.

**Solution:** Train LSTM on real drowning data and replace dummy model.

## Performance Tips

### For Faster Processing
Edit these lines in `test_video_analysis.py`:

```python
FRAME_SKIP = 4          # Process every 4th frame (line 21)
RESIZE_FOR_POSE = 384   # Smaller resize (line 22)
CONFIDENCE_THRESHOLD = 0.6  # Higher threshold (line 23)
```

### For Better Accuracy
```python
FRAME_SKIP = 1          # Process every frame
RESIZE_FOR_POSE = 640   # Larger resize
CONFIDENCE_THRESHOLD = 0.3  # Lower threshold
```

## Example Workflow

1. **Get a test video:**
   ```bash
   # Download a sample swimming video
   # Or use your own pool surveillance footage
   ```

2. **Run analysis:**
   ```bash
   python test_video_analysis.py --video pool_video.mp4
   ```

3. **Watch live preview:**
   - See real-time risk assessment
   - Monitor LSTM risk scores
   - Check pose detection quality

4. **Review output video:**
   ```bash
   # Open output_analysis.mp4 in video player
   # Review frame-by-frame if needed
   ```

5. **Check statistics:**
   - Review console output
   - Analyze risk distribution
   - Verify pose detection rate

## Understanding Risk Scores

### LSTM Risk Scores (3 probabilities)
- **[0.92, 0.06, 0.02]** = 92% SAFE, 6% WARNING, 2% DANGER
- **[0.30, 0.50, 0.20]** = 30% SAFE, 50% WARNING, 20% DANGER
- **[0.10, 0.20, 0.70]** = 10% SAFE, 20% WARNING, 70% DANGER

### Risk State (highest probability)
- Max probability determines state
- Confidence = max(probabilities)
- Higher confidence = more certain prediction

### Buffer Status
- **0-29 frames**: Not ready for inference
- **30-89 frames**: Inference active, building history
- **90 frames**: Full buffer, optimal inference

## Next Steps

1. **Test with different videos:**
   - Normal swimming
   - Diving
   - Struggling (simulated)
   - Different camera angles

2. **Collect training data:**
   - Record videos with labeled behaviors
   - Extract feature sequences
   - Prepare dataset for LSTM training

3. **Train LSTM model:**
   - Use collected data
   - Replace dummy model
   - Validate on test set

4. **Deploy to production:**
   - Integrate with main system
   - Monitor performance
   - Tune thresholds

---

**Happy Testing!** 🎥🏊‍♂️

For questions or issues, check the main documentation in `doc/` folder.
