# How to Get Better Drowning Detection

## Current Situation

The system currently shows **mostly SAFE** predictions because:

1. **Dummy LSTM Model** - Not trained on real drowning data
2. **Safety Bias** - Intentionally biased towards SAFE during testing
3. **No Training Data** - The model has never seen actual drowning behaviors

## Why the Enhanced Version is Better

### ✅ **test_enhanced_analysis.py** vs **test_video_analysis.py**

| Feature | Basic Version | Enhanced Version |
|---------|--------------|------------------|
| **Tracking** | Simple frame-by-frame IDs | DeepSORT persistent tracking |
| **Pose Visualization** | ❌ None | ✅ Full skeleton overlay |
| **Behavior Classification** | ❌ None | ✅ 5 behaviors (SWIMMING, DIVING, FLOATING, STRUGGLING, DROWNING) |
| **State Machine** | ❌ None | ✅ 4 states (SAFE, ATTENTION, WARNING, DANGER) |
| **Temporal Analysis** | ❌ None | ✅ 90-frame rolling buffer |
| **Risk Assessment** | LSTM only | Behavior + LSTM combined |

### 🎯 **What You See in Enhanced Version**

1. **Persistent Track IDs** - Same person keeps same ID across frames
2. **Pose Skeleton** - Magenta keypoints and connections
3. **Behavior Labels** - "SWIMMING", "STRUGGLING", etc.
4. **State Progression** - SAFE → ATTENTION → WARNING → DANGER
5. **Tracking Duration** - How long each person has been tracked

## How to Get Accurate Drowning Detection

### 📊 **Step 1: Collect Training Data**

You need labeled video sequences showing:

**SAFE Behaviors:**
- Normal swimming (freestyle, breaststroke, backstroke)
- Floating calmly
- Diving and resurfacing
- Playing in water
- Standing/walking in shallow water

**WARNING Behaviors:**
- Struggling to stay afloat
- Erratic arm movements
- Head bobbing up and down
- Gasping for air
- Vertical body position with minimal forward movement

**DANGER Behaviors:**
- Passive drowning (no movement)
- Face-down floating
- Submerged for extended period
- Arms unable to move
- Ladder climb motion (instinctive drowning response)

### 📝 **Step 2: Label Your Data**

For each video sequence, create labels like:

```json
{
  "video": "pool_video_001.mp4",
  "sequences": [
    {
      "start_frame": 0,
      "end_frame": 300,
      "track_id": 1,
      "label": "SAFE",
      "behavior": "SWIMMING"
    },
    {
      "start_frame": 301,
      "end_frame": 450,
      "track_id": 1,
      "label": "WARNING",
      "behavior": "STRUGGLING"
    },
    {
      "start_frame": 451,
      "end_frame": 600,
      "track_id": 1,
      "label": "DANGER",
      "behavior": "DROWNING"
    }
  ]
}
```

### 🔧 **Step 3: Extract Features**

Run the enhanced analysis to extract features:

```python
# Create feature extraction script
import json
from pathlib import Path

# Process all labeled videos
for video_file in labeled_videos:
    # Run pose detection
    # Extract 4 LSTM features per frame:
    #   1. vertical_ratio
    #   2. arm_velocity  
    #   3. horizontal_displacement
    #   4. head_oscillation
    
    # Save features with labels
    features_data = {
        'features': feature_sequences,  # (N, 90, 4)
        'labels': label_sequences,      # (N,) - 0=SAFE, 1=WARNING, 2=DANGER
        'track_ids': track_ids
    }
    
    save_features(features_data, f"features_{video_file.stem}.npz")
```

### 🧠 **Step 4: Train LSTM Model**

```python
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from core.behavior.temporal_model import TemporalLSTMClassifier

# Load all feature files
all_features = []
all_labels = []

for feature_file in Path("features/").glob("*.npz"):
    data = np.load(feature_file)
    all_features.append(data['features'])
    all_labels.append(data['labels'])

X = np.concatenate(all_features)  # (N, 90, 4)
y = np.concatenate(all_labels)    # (N,)

# Split train/val/test
from sklearn.model_selection import train_test_split
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

# Create dataloaders
train_dataset = TensorDataset(
    torch.FloatTensor(X_train),
    torch.LongTensor(y_train)
)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

val_dataset = TensorDataset(
    torch.FloatTensor(X_val),
    torch.LongTensor(y_val)
)
val_loader = DataLoader(val_dataset, batch_size=32)

# Initialize model
model = TemporalLSTMClassifier(input_size=4, hidden_size=32, output_size=3)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# Training loop
num_epochs = 50
best_val_acc = 0

for epoch in range(num_epochs):
    model.train()
    train_loss = 0
    
    for features, labels in train_loader:
        optimizer.zero_grad()
        logits, probs = model(features)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
    
    # Validation
    model.eval()
    correct = 0
    total = 0
    
    with torch.no_grad():
        for features, labels in val_loader:
            logits, probs = model(features)
            _, predicted = torch.max(probs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    val_acc = correct / total
    
    print(f"Epoch {epoch+1}/{num_epochs}")
    print(f"  Train Loss: {train_loss/len(train_loader):.4f}")
    print(f"  Val Accuracy: {val_acc:.4f}")
    
    # Save best model
    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save({
            'model_state_dict': model.state_dict(),
            'input_size': 4,
            'hidden_size': 32,
            'output_size': 3,
            'val_accuracy': val_acc
        }, 'weights/behavior/drowning_lstm.pt')
        print(f"  ✅ Saved new best model (acc: {val_acc:.4f})")

print(f"\n✅ Training complete! Best validation accuracy: {best_val_acc:.4f}")
```

### 🎯 **Step 5: Tune Thresholds**

After training, tune the risk thresholds in `core/config.py`:

```python
# Current defaults
LSTM_DANGER_THRESHOLD = 0.7   # P(DANGER) > 0.7 → DANGER state
LSTM_WARNING_THRESHOLD = 0.4  # P(WARNING) > 0.4 → WARNING state

# Tune based on validation results
# Lower thresholds = more sensitive (more false alarms)
# Higher thresholds = less sensitive (may miss drowning)

# Example: More sensitive
LSTM_DANGER_THRESHOLD = 0.5   # Trigger DANGER earlier
LSTM_WARNING_THRESHOLD = 0.3  # Trigger WARNING earlier

# Example: Less sensitive (fewer false alarms)
LSTM_DANGER_THRESHOLD = 0.8   # Only trigger on very confident predictions
LSTM_WARNING_THRESHOLD = 0.5  # Higher bar for WARNING
```

### 📈 **Step 6: Validate on Test Set**

```python
# Test on held-out data
model.eval()
test_dataset = TensorDataset(
    torch.FloatTensor(X_test),
    torch.LongTensor(y_test)
)
test_loader = DataLoader(test_dataset, batch_size=32)

# Confusion matrix
from sklearn.metrics import confusion_matrix, classification_report

all_preds = []
all_labels = []

with torch.no_grad():
    for features, labels in test_loader:
        logits, probs = model(features)
        _, predicted = torch.max(probs, 1)
        all_preds.extend(predicted.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

# Print results
print("\nConfusion Matrix:")
print(confusion_matrix(all_labels, all_preds))

print("\nClassification Report:")
print(classification_report(all_labels, all_preds, 
                          target_names=['SAFE', 'WARNING', 'DANGER']))
```

## Expected Improvements

### Before Training (Dummy Model)
```
Risk Distribution:
  SAFE: 95%
  WARNING: 4%
  DANGER: 1%
```

### After Training (Real Model)
```
Risk Distribution:
  SAFE: 70%
  WARNING: 20%
  DANGER: 10%

Accuracy on Test Set:
  SAFE: 92%
  WARNING: 85%
  DANGER: 88%
```

## Alternative: Improve Behavior Classification

If you don't have drowning training data, you can improve the **behavior classification** thresholds:

### Edit `core/behavior_classification/behavior_patterns.py`

```python
# Make struggling detection more sensitive
STRUGGLING_PATTERNS = {
    'vertical_angle': (60, 90),      # More vertical (was 70-90)
    'arms_above_shoulders': True,
    'arms_extended': (0.3, 0.7),     # Moderate extension (was 0.4-0.7)
    'velocity': (0.05, 0.15),        # Lower threshold (was 0.1-0.2)
    'acceleration': (0.03, float('inf'))  # Lower threshold (was 0.05)
}

# Make drowning detection more sensitive
DROWNING_PATTERNS = {
    'vertical_angle': (70, 90),      # Very vertical (was 80-90)
    'depth_ratio': (0.6, 1.0),       # Lower in water (was 0.7-1.0)
    'velocity': (0.0, 0.05),         # Very slow (was 0.0-0.03)
    'arms_extended': (0.0, 0.3),     # Arms not moving (was 0.0-0.2)
    'face_up': False
}
```

### Edit `core/behavior_classification/state_machine.py`

```python
# Make state transitions faster
STATE_TRANSITIONS = {
    'SAFE': {
        'STRUGGLING': 10,    # Frames needed (was 15)
        'DROWNING': 20       # Frames needed (was 30)
    },
    'ATTENTION': {
        'WARNING': 15,       # Frames needed (was 30)
        'SAFE': 20           # Frames to recover (was 30)
    },
    'WARNING': {
        'DANGER': 30,        # Frames needed (was 60)
        'SAFE': 30           # Frames to recover (was 45)
    }
}
```

## Summary

**For best results:**
1. ✅ Use `test_enhanced_analysis.py` (full pipeline)
2. ✅ Collect and label real drowning videos
3. ✅ Train LSTM on your data
4. ✅ Tune thresholds based on validation
5. ✅ Test on held-out data

**Quick improvements without training:**
1. ✅ Adjust behavior pattern thresholds
2. ✅ Tune state transition frame counts
3. ✅ Lower LSTM thresholds (more sensitive)

**Remember:** The dummy LSTM model is intentionally conservative (biased towards SAFE) for safety during testing. Real drowning detection requires real training data!

---

**Current Status:** ✅ System architecture complete and working  
**Next Step:** Collect training data for LSTM model  
**Expected Timeline:** 1-2 weeks for data collection + 1 day for training
