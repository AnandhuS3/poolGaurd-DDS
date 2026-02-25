# Training Guide - Person Classification & Model Fine-Tuning

## Overview

This guide explains how to:
1. **Classify persons as CHILD or ADULT** based on size
2. **Use ensemble detection** with `best.pt` and `best1.pt`
3. **Fine-tune YOLOv8-pose** for better pose estimation
4. **Train LSTM** on your drowning data

## New Features

### 1. Person Size Classification

Automatically classifies detected persons as **CHILD** or **ADULT** based on:
- Bounding box height/width relative to frame
- Bounding box area
- Aspect ratio
- Shoulder width (from pose keypoints)
- Head-to-torso ratio (from pose keypoints)

**Usage:**
```python
from core.person_classifier import PersonSizeClassifier

classifier = PersonSizeClassifier()

# Classify from bounding box
bbox = (x1, y1, x2, y2)
size, metrics = classifier.classify_from_bbox(
    bbox, frame_height, frame_width, keypoints=None
)

print(f"Person size: {size.value}")  # 'child' or 'adult'
```

**With pose keypoints (more accurate):**
```python
size, metrics = classifier.classify_from_bbox(
    bbox, frame_height, frame_width, keypoints=pose_keypoints
)
```

### 2. Ensemble Detection

Combines detections from multiple YOLO models for better accuracy:

**Usage:**
```python
from core.person_classifier import EnsembleDetector

# Initialize with your models
detector = EnsembleDetector(
    model_paths=['weights/best.pt', 'weights/best1.pt'],
    weights=[0.6, 0.4],  # Give more weight to best.pt
    nms_threshold=0.5,
    confidence_threshold=0.5
)

# Detect persons
detections = detector.detect(frame)

for det in detections:
    bbox = det['bbox']
    confidence = det['confidence']  # Weighted confidence
    class_id = det['class']
```

## Training Pipeline

### Step 1: Prepare Your Data

Create the following directory structure:

```
data/drowning/
├── videos/
│   ├── video_001.mp4
│   ├── video_002.mp4
│   └── ...
├── labels/
│   ├── video_001.json
│   ├── video_002.json
│   └── ...
├── pose_annotations/
│   ├── images/
│   │   ├── img_001.jpg
│   │   └── ...
│   └── annotations.json  # COCO format
└── annotations.json
```

### Step 2: Label Your Videos

Create label files in `labels/` directory:

**Example: `video_001.json`**
```json
{
  "video_id": "video_001",
  "sequences": [
    {
      "track_id": 1,
      "start_frame": 0,
      "end_frame": 300,
      "label": 0,
      "behavior": "SWIMMING",
      "person_size": "adult"
    },
    {
      "track_id": 1,
      "start_frame": 301,
      "end_frame": 450,
      "label": 1,
      "behavior": "STRUGGLING",
      "person_size": "adult"
    },
    {
      "track_id": 2,
      "start_frame": 0,
      "end_frame": 600,
      "label": 0,
      "behavior": "SWIMMING",
      "person_size": "child"
    }
  ]
}
```

**Labels:**
- `0` = SAFE
- `1` = WARNING
- `2` = DANGER

**Person Size:**
- `"child"` = Child
- `"adult"` = Adult
- `"unknown"` = Unknown

### Step 3: Create annotations.json

**Example: `annotations.json`**
```json
{
  "samples": [
    {
      "video_id": "video_001",
      "track_id": 1,
      "start_frame": 0,
      "label": 0,
      "person_size": "adult",
      "split": "train"
    },
    {
      "video_id": "video_001",
      "track_id": 1,
      "start_frame": 301,
      "label": 1,
      "person_size": "adult",
      "split": "train"
    },
    {
      "video_id": "video_002",
      "track_id": 1,
      "start_frame": 0,
      "label": 2,
      "person_size": "child",
      "split": "val"
    }
  ]
}
```

**Splits:**
- `"train"` - 70% of data
- `"val"` - 15% of data
- `"test"` - 15% of data

### Step 4: Extract Features

Extract LSTM features from your labeled videos:

```bash
python train_models.py --task extract --data-dir data/drowning
```

This will:
1. Use ensemble detection (`best.pt` + `best1.pt`)
2. Run pose estimation
3. Extract 4 features per frame
4. Create 90-frame sequences
5. Save to `data/drowning/features/`

**Output:**
```
data/drowning/features/
├── video_001_1_0.npy        # Features (90, 4)
├── video_001_1_0.json       # Metadata
├── video_001_1_30.npy
├── video_001_1_30.json
└── ...
```

### Step 5: Train LSTM Model

Train the LSTM classifier on extracted features:

```bash
python train_models.py --task train-lstm --data-dir data/drowning --epochs 50 --batch-size 32
```

**Training output:**
```
======================================================================
Training LSTM Drowning Risk Classifier
======================================================================

Epoch 1/50
----------------------------------------------------------------------
Training: 100%|████████████| 125/125 [00:15<00:00,  8.12it/s]
Validation: 100%|██████████| 25/25 [00:02<00:00, 10.45it/s]

Results:
  Train Loss: 0.8234 | Train Acc: 0.6543
  Val Loss:   0.7456 | Val Acc:   0.6892

  Per-class Accuracy:
    SAFE:    0.8234 (412/500)
    WARNING: 0.6543 (98/150)
    DANGER:  0.5234 (52/100)

  ✅ Saved new best model (val_acc: 0.6892)

...

Epoch 50/50
----------------------------------------------------------------------
Results:
  Train Loss: 0.2145 | Train Acc: 0.9234
  Val Loss:   0.2567 | Val Acc:   0.9123

  Per-class Accuracy:
    SAFE:    0.9456 (473/500)
    WARNING: 0.8867 (133/150)
    DANGER:  0.8800 (88/100)

  ✅ Saved new best model (val_acc: 0.9123)

======================================================================
Training Complete!
Best Validation Accuracy: 0.9123
Model saved to: weights/behavior/drowning_lstm.pt
======================================================================
```

### Step 6: Fine-Tune Pose Model (Optional)

If you have pose annotations, fine-tune YOLOv8-pose:

**Create `data/drowning/data.yaml`:**
```yaml
path: data/drowning/pose_annotations
train: images
val: images

# Keypoint shape: [num_keypoints, 3] (x, y, visibility)
kpt_shape: [17, 3]

# Keypoint names (COCO format)
names:
  0: person

# Keypoint connections for visualization
flip_idx: [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15]
```

**Run fine-tuning:**
```bash
python train_models.py --task finetune-pose --data-dir data/drowning --epochs 100 --batch-size 16
```

**Output:**
```
======================================================================
Fine-tuning YOLOv8-Pose Model
======================================================================

Epoch 1/100: 100%|████████| 125/125 [01:23<00:00,  1.50it/s]
      Class     Images  Instances      Box(P          R      mAP50  mAP50-95)
        all        500       1250      0.654      0.723      0.689      0.456
       Pose(P          R      mAP50  mAP50-95)
              0.623      0.698      0.654      0.412

...

Epoch 100/100: 100%|████████| 125/125 [01:20<00:00,  1.56it/s]
      Class     Images  Instances      Box(P          R      mAP50  mAP50-95)
        all        500       1250      0.892      0.876      0.923      0.678
       Pose(P          R      mAP50  mAP50-95)
              0.867      0.854      0.901      0.645

======================================================================
Fine-tuning Complete!
Model saved to: weights/behavior/yolov8n-pose-finetuned/weights/best.pt
======================================================================
```

### Step 7: Run All Tasks

Run everything in one command:

```bash
python train_models.py --task all --data-dir data/drowning --epochs 50
```

This will:
1. Extract features from videos
2. Train LSTM model
3. Fine-tune pose model

## Using Trained Models

### Update Configuration

Edit `core/config.py`:

```python
# Use ensemble detection
USE_ENSEMBLE_DETECTION = True
ENSEMBLE_MODELS = [
    MODEL_DIR / "best.pt",
    MODEL_DIR / "best1.pt"
]
ENSEMBLE_WEIGHTS = [0.6, 0.4]  # Weights for each model

# Use fine-tuned pose model
POSE_MODEL_PATH = MODEL_DIR / "behavior" / "yolov8n-pose-finetuned" / "weights" / "best.pt"

# Use trained LSTM
LSTM_MODEL_PATH = MODEL_DIR / "behavior" / "drowning_lstm.pt"

# Enable person size classification
USE_PERSON_SIZE_CLASSIFICATION = True
CHILD_HEIGHT_THRESHOLD = 0.35  # Adjust based on your camera setup
ADULT_HEIGHT_THRESHOLD = 0.50
```

### Test with Enhanced Analysis

```bash
python test_enhanced_analysis.py --video test_video.mp4
```

You should now see:
- ✅ Better person detection (ensemble)
- ✅ More accurate pose estimation (fine-tuned)
- ✅ Realistic drowning risk scores (trained LSTM)
- ✅ Person size labels (CHILD/ADULT)

## Expected Improvements

### Before Training

```
Risk Distribution:
  SAFE: 95%
  WARNING: 4%
  DANGER: 1%

Pose Detection Rate: 60%
Person Classification: None
```

### After Training

```
Risk Distribution:
  SAFE: 70%
  WARNING: 20%
  DANGER: 10%

LSTM Accuracy:
  SAFE: 94.5%
  WARNING: 88.7%
  DANGER: 88.0%

Pose Detection Rate: 85% (fine-tuned)
Person Classification: CHILD/ADULT (95% accuracy)
```

## Troubleshooting

### Issue: Low LSTM accuracy

**Solutions:**
1. Collect more training data (aim for 1000+ sequences)
2. Balance your dataset (equal SAFE/WARNING/DANGER samples)
3. Increase sequence length (try 120 frames = 4 seconds)
4. Add data augmentation
5. Tune hyperparameters (learning rate, hidden size)

### Issue: Pose detection still poor

**Solutions:**
1. Collect more pose annotations (aim for 5000+ images)
2. Include diverse scenarios (different angles, lighting, occlusion)
3. Increase training epochs (try 200)
4. Use larger model (yolov8m-pose or yolov8l-pose)
5. Adjust augmentation parameters

### Issue: Person size classification incorrect

**Solutions:**
1. Adjust thresholds in config:
   ```python
   CHILD_HEIGHT_THRESHOLD = 0.30  # Lower for smaller children
   ADULT_HEIGHT_THRESHOLD = 0.55  # Higher for taller adults
   ```
2. Calibrate based on your camera height and angle
3. Use pose keypoints for better accuracy

## Advanced: Continuous Learning

Enable the system to improve over time:

```python
# In core/config.py
ENABLE_CONTINUOUS_LEARNING = True
SAVE_PREDICTIONS_FOR_REVIEW = True
PREDICTION_LOG_DIR = Path("data/predictions")

# Periodically review predictions
# Label incorrect predictions
# Retrain model with new data
```

## Summary

**Complete Training Workflow:**

1. ✅ Collect videos of swimming pool
2. ✅ Label sequences (SAFE/WARNING/DANGER)
3. ✅ Mark person sizes (CHILD/ADULT)
4. ✅ Extract features: `python train_models.py --task extract`
5. ✅ Train LSTM: `python train_models.py --task train-lstm`
6. ✅ (Optional) Fine-tune pose: `python train_models.py --task finetune-pose`
7. ✅ Update config with trained models
8. ✅ Test with enhanced analysis
9. ✅ Deploy to production

**Expected Timeline:**
- Data collection: 1-2 weeks
- Labeling: 2-3 days
- Feature extraction: 1-2 hours
- LSTM training: 1-2 hours
- Pose fine-tuning: 4-6 hours
- Testing & validation: 1 day

**Total: ~2-3 weeks for complete training pipeline**

---

**🎉 You now have a complete, trainable drowning detection system!**
