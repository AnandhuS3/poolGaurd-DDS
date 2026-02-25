# Quick Start Guide - Pose-Driven Detection

## Prerequisites

- Python 3.8+
- Existing DDS v4 installation
- Internet connection (for model download)

## Installation (5 minutes)

### Step 1: Install Dependencies

```bash
# Navigate to project directory
cd c:\Users\Anandhu\Desktop\poj\ARk_2\mini_project\DDS\v4

# Install ultralytics for YOLOv8-pose
pip install ultralytics
```

### Step 2: Verify Configuration

The pose-driven system is **enabled by default**. Check `core/config.py`:

```python
USE_POSE_ESTIMATION = True  # Should be True
FALLBACK_TO_HEURISTIC = True  # Should be True for safety
```

### Step 3: Start Server

```bash
python main.py
```

**Expected Output:**
```
=============================================================
  🏊 PoolGaurd - Drowning Detection System
=============================================================

🌐 Server: http://0.0.0.0:8000
🔐 Login: http://localhost:8000/login
...
✅ Pose-driven detection pipeline enabled
   Model: yolov8-pose
   Temporal window: 90 frames
   Fallback: Enabled
```

**If you see:**
```
⚠️  Pose-driven detection not available - using legacy heuristic
```

This means the pose model is downloading or there's an issue. Check logs:
```bash
tail -f dlogs/video.log
```

## Testing (10 minutes)

### Test 1: Verify Pose Detection

1. **Open browser:** http://localhost:8000
2. **Login:** admin@dds.local / admin123
3. **Upload a video** with people swimming
4. **Click "Start Analysis"**
5. **Check the labels** on bounding boxes:
   - Should show: `ID:1 SAFE (swimming)`
   - Or: `ID:2 WARNING (struggling)`

**If you see behavior labels** → Pose-driven is working! ✅

**If you only see** `ID:1 SAFE` → Using heuristic fallback

### Test 2: Check WebSocket Output

Open browser console (F12) and look for WebSocket messages:

```json
{
  "type": "frame",
  "persons": [
    {
      "id": 1,
      "behavior": "swimming",        // NEW
      "pose_available": true         // NEW
    }
  ]
}
```

**If `pose_available: true`** → Pose detection working! ✅

### Test 3: Monitor Logs

```bash
# In another terminal
tail -f dlogs/video.log | grep -E "POSE|HEURISTIC"
```

**Expected:**
```
[POSE] Person #1: SAFE (behavior: swimming)
[POSE] Person #2: WARNING (behavior: struggling)
```

**If you see `[HEURISTIC]`** → System is using fallback

## Troubleshooting

### Issue: Pose model not downloading

**Solution:**
```bash
# Download manually
cd weights
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt

# Or use curl on Windows
curl -L https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt -o yolov8n-pose.pt
```

### Issue: "ModuleNotFoundError: No module named 'ultralytics'"

**Solution:**
```bash
pip install ultralytics
```

### Issue: Low FPS (< 10 FPS)

**Solution 1:** Reduce processing frequency
```python
# In core/config.py
BEHAVIOR_UPDATE_INTERVAL = 3  # Process every 3 frames instead of every frame
```

**Solution 2:** Disable pose visualization
```python
# In core/config.py
VISUALIZE_POSE = False  # Already default
```

**Solution 3:** Use GPU
```bash
# Install CUDA-enabled PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Issue: Want to use legacy heuristic only

**Solution:**
```python
# In core/config.py
USE_POSE_ESTIMATION = False
```

Restart server:
```bash
python main.py
```

## Verification Checklist

- [ ] Server starts without errors
- [ ] Logs show "Pose-driven detection pipeline enabled"
- [ ] Video processing works
- [ ] Bounding boxes show behavior labels (e.g., "swimming")
- [ ] WebSocket output includes `behavior` and `pose_available` fields
- [ ] FPS is acceptable (>15 on CPU, >30 on GPU)

## Next Steps

### For Testing
1. Test with different videos (swimming, diving, struggling)
2. Monitor false positives/negatives
3. Adjust thresholds in `core/config.py` if needed

### For Production
1. Tune behavior thresholds based on real data
2. Optimize performance (GPU, frame skip)
3. Disable fallback if pose is reliable:
   ```python
   FALLBACK_TO_HEURISTIC = False
   ```

### For Development
1. Read `doc/POSE_DRIVEN_README.md` for detailed documentation
2. Review `doc/POSE_DRIVEN_REFACTOR_PLAN.md` for architecture
3. Check `doc/POSE_DRIVEN_SUMMARY.md` for implementation details

## Support

**Logs:**
```bash
# Video processing logs
tail -f dlogs/video.log

# Model loading logs
tail -f dlogs/model.log

# Detection logs
tail -f dlogs/detection.log
```

**Configuration:**
- Main config: `core/config.py`
- Credentials: `core/credentials.py`
- Paths: `core/paths.py`

**Rollback:**
```python
# Instant rollback to legacy
USE_POSE_ESTIMATION = False
```

---

**Ready to test!** 🚀

If you encounter any issues, check the logs first, then refer to the troubleshooting section above.
