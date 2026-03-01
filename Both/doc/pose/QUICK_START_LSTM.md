# Quick Start - LSTM Risk Inference

## Prerequisites

- DDS v4 with pose-driven detection already installed
- Python 3.8+
- PyTorch installed

## Installation (5 minutes)

### Step 1: Install PyTorch (if not already installed)

```bash
# CPU-only version (recommended for LSTM)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# OR GPU version (if you have CUDA)
pip install torch torchvision
```

### Step 2: Verify Configuration

The LSTM system is **enabled by default**. Check `core/config.py`:

```python
USE_SECONDARY_POSE = True       # Should be True
USE_LSTM_CLASSIFIER = True      # Should be True
SECONDARY_POSE_FRAME_SKIP = 2   # Process every 2nd frame
LSTM_BUFFER_SIZE = 90           # 3 seconds @ 30 FPS
```

### Step 3: Create Model Directory

```bash
# Create directory for LSTM models
mkdir -p weights\behavior
```

### Step 4: Start Server

```bash
python main.py
```

**Expected Output:**
```
=============================================================
  🏊 PoolGaurd - Drowning Detection System
=============================================================

✅ Pose-driven detection pipeline enabled
✅ LSTM risk inference enabled
   Secondary pose model: weights/behavior/yolov8n-pose.pt
   LSTM model: weights/behavior/drowning_lstm.pt
   Buffer size: 90 frames
   Frame skip: 1:2
   Resize: 512px
```

**If you see:**
```
⚠️  LSTM model not found at weights/behavior/drowning_lstm.pt
Creating dummy LSTM model for testing...
✅ Dummy LSTM model saved
```

This is **normal** - a dummy model is auto-created for testing.

---

## Testing (10 minutes)

### Test 1: Verify LSTM Inference

1. **Upload a video** with people swimming
2. **Open browser console** (F12)
3. **Monitor WebSocket messages:**

```javascript
// In browser console
let ws = new WebSocket('ws://localhost:8000/ws/analyze/123');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'frame' && data.persons.length > 0) {
        const person = data.persons[0];
        console.log('LSTM Risk State:', person.lstm_risk_state);
        console.log('LSTM Scores:', person.lstm_risk_scores);
        console.log('LSTM Confidence:', person.lstm_confidence);
        console.log('LSTM Available:', person.lstm_available);
    }
};
```

**Expected Output:**
```
LSTM Risk State: SAFE
LSTM Scores: [0.92, 0.06, 0.02]  // [SAFE, WARNING, DANGER]
LSTM Confidence: 0.92
LSTM Available: true
```

### Test 2: Check Logs

```bash
# Monitor LSTM inference
tail -f dlogs/video.log | grep -E "LSTM|lstm"
```

**Expected:**
```
[INFO] ✅ LSTM risk inference enabled
[DEBUG] [LSTM] Person #1: Buffer size 45/90
[DEBUG] [LSTM] Person #1: Inference ready (90 frames)
```

### Test 3: Verify Frame Skip

```bash
# Check that LSTM processes every 2nd frame
tail -f dlogs/video.log | grep "LSTM inference"
```

You should see LSTM processing at half the frame rate.

---

## Understanding the Output

### LSTM Risk Scores

```json
{
  "lstm_risk_state": "SAFE",           // Current risk level
  "lstm_risk_scores": [0.92, 0.06, 0.02],  // Probabilities
  "lstm_confidence": 0.92,             // Max probability
  "lstm_available": true               // LSTM succeeded
}
```

**Risk Scores Array:**
- `[0]` = P(SAFE) - Normal swimming/floating
- `[1]` = P(WARNING) - Struggling/distress
- `[2]` = P(DANGER) - Drowning

**Interpretation:**
- `lstm_confidence > 0.8` = High confidence
- `lstm_confidence 0.5-0.8` = Medium confidence
- `lstm_confidence < 0.5` = Low confidence

### 4 Extracted Features

The LSTM uses these features (visible in logs with DEBUG level):

1. **vertical_ratio** (0-1): Position in frame
   - 0.0 = Top of frame
   - 0.6+ = Bottom (submerged)
   
2. **arm_velocity** (0-1): Arm movement speed
   - 0.0 = No movement
   - 0.5+ = Active swimming
   
3. **horizontal_displacement** (0-1): Lateral movement
   - 0.0 = Stationary
   - 0.3+ = Moving horizontally
   
4. **head_oscillation** (0-1): Head bobbing
   - 0.0 = Still
   - 0.3+ = Struggling/bobbing

---

## Configuration Options

### Adjust Frame Skip (for performance)

```python
# In core/config.py

# Process every frame (slower, more accurate)
SECONDARY_POSE_FRAME_SKIP = 1

# Process every 3rd frame (faster, less accurate)
SECONDARY_POSE_FRAME_SKIP = 3
```

### Adjust Buffer Size

```python
# 2-second buffer (faster inference, less context)
LSTM_BUFFER_SIZE = 60

# 5-second buffer (slower inference, more context)
LSTM_BUFFER_SIZE = 150
```

### Adjust Risk Thresholds

```python
# More sensitive (earlier warnings)
LSTM_DANGER_THRESHOLD = 0.5
LSTM_WARNING_THRESHOLD = 0.3

# Less sensitive (fewer false positives)
LSTM_DANGER_THRESHOLD = 0.8
LSTM_WARNING_THRESHOLD = 0.5
```

### Disable LSTM Only

```python
# Keep pose-driven, disable LSTM
USE_LSTM_CLASSIFIER = False
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'torch'"

**Solution:**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Issue: LSTM always returns [1.0, 0.0, 0.0]

**Expected behavior** with dummy model. The dummy model is biased towards SAFE for safety.

**Solution:** Train a real LSTM model on labeled drowning data.

### Issue: Low FPS (< 10 FPS)

**Solution 1:** Increase frame skip
```python
SECONDARY_POSE_FRAME_SKIP = 3  # Process every 3rd frame
```

**Solution 2:** Reduce buffer size
```python
LSTM_BUFFER_SIZE = 60  # 2 seconds instead of 3
```

**Solution 3:** Disable LSTM
```python
USE_LSTM_CLASSIFIER = False
```

### Issue: "lstm_available: false" in output

**Possible causes:**
1. Not enough frames yet (need 30+ frames)
2. Pose detection failed for this track
3. Feature extraction failed

**Check logs:**
```bash
tail -f dlogs/video.log | grep "Person #1"
```

### Issue: Secondary pose model downloading slowly

**Solution:** Download manually
```bash
cd weights/behavior
curl -L https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n-pose.pt -o yolov8n-pose.pt
```

---

## Performance Tuning

### For High FPS (30+ FPS)

```python
# Aggressive frame skip
SECONDARY_POSE_FRAME_SKIP = 4

# Smaller buffer
LSTM_BUFFER_SIZE = 60

# Smaller resize
SECONDARY_POSE_RESIZE = 384
```

### For High Accuracy

```python
# Process every frame
SECONDARY_POSE_FRAME_SKIP = 1

# Larger buffer
LSTM_BUFFER_SIZE = 120

# Larger resize
SECONDARY_POSE_RESIZE = 640
```

### For Low Memory

```python
# Smaller buffer
LSTM_BUFFER_SIZE = 45  # 1.5 seconds

# Disable if not needed
USE_LSTM_CLASSIFIER = False
```

---

## Training Your Own LSTM Model

### Step 1: Collect Data

1. Record videos of:
   - Normal swimming (label: SAFE)
   - Struggling/distress (label: WARNING)
   - Drowning/passive (label: DANGER)

2. Process videos to extract features:
```python
from core.behavior.behavior_features import BehaviorFeatureExtractor

extractor = BehaviorFeatureExtractor()
# Extract features from each frame
# Create sequences of 90 frames
# Label each sequence
```

### Step 2: Train Model

```python
import torch
import torch.nn as nn
from core.behavior.temporal_model import TemporalLSTMClassifier

# Load your training data
# X_train: (num_samples, 90, 4)
# y_train: (num_samples,) - labels 0/1/2

model = TemporalLSTMClassifier(input_size=4, hidden_size=32, output_size=3)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# Training loop
for epoch in range(100):
    for X_batch, y_batch in train_loader:
        optimizer.zero_grad()
        logits, _ = model(X_batch)
        loss = criterion(logits, y_batch)
        loss.backward()
        optimizer.step()
    
    print(f"Epoch {epoch}, Loss: {loss.item()}")

# Save trained model
torch.save({
    'model_state_dict': model.state_dict(),
    'input_size': 4,
    'hidden_size': 32,
    'output_size': 3
}, 'weights/behavior/drowning_lstm.pt')
```

### Step 3: Replace Dummy Model

```bash
# Backup dummy model
mv weights/behavior/drowning_lstm.pt weights/behavior/drowning_lstm_dummy.pt

# Copy your trained model
cp your_trained_model.pt weights/behavior/drowning_lstm.pt

# Restart server
python main.py
```

---

## Verification Checklist

- [ ] PyTorch installed (`pip list | grep torch`)
- [ ] Server starts without errors
- [ ] Logs show "✅ LSTM risk inference enabled"
- [ ] Dummy model auto-created (if no trained model)
- [ ] WebSocket output includes `lstm_*` fields
- [ ] `lstm_available: true` for tracked persons
- [ ] Risk scores update in real-time
- [ ] FPS acceptable (>15 on CPU)

---

## Next Steps

### For Testing
1. Test with different videos (swimming, diving, struggling)
2. Monitor LSTM risk scores vs actual behavior
3. Adjust thresholds if needed

### For Production
1. Collect labeled drowning video dataset
2. Train LSTM on real data
3. Validate on test set
4. Deploy trained model
5. Monitor false positive/negative rates

### For Development
1. Read `doc/LSTM_INTEGRATION_GUIDE.md` for detailed docs
2. Review `core/behavior/` module code
3. Experiment with different features
4. Try different LSTM architectures

---

## Support

**Logs:**
```bash
# LSTM-specific logs
tail -f dlogs/video.log | grep LSTM

# Feature extraction logs
tail -f dlogs/video.log | grep "Feature"

# All logs
tail -f dlogs/video.log
```

**Configuration:**
- Main config: `core/config.py`
- LSTM settings: Lines 171-188

**Disable LSTM:**
```python
# Instant disable
USE_LSTM_CLASSIFIER = False
```

---

**Ready to test!** 🚀

The LSTM system is now integrated and ready for testing with the dummy model. Replace with a trained model for production use.

**Note:** The dummy model always predicts SAFE with high confidence. This is intentional for safety during testing.
