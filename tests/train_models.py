"""
Training Pipeline for Drowning Detection Models
Trains/fine-tunes:
1. YOLOv8-pose for better pose estimation
2. LSTM for drowning risk classification
3. Uses best.pt and best1.pt for ensemble detection
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np
import cv2
from pathlib import Path
from typing import List, Dict, Tuple
import json
from tqdm import tqdm
import yaml

from ultralytics import YOLO
from core.behavior.temporal_model import TemporalLSTMClassifier
from core.behavior.behavior_features import BehaviorFeatureExtractor
from core.pose_estimation.pose_detector import PoseDetector


class DrowningDataset(Dataset):
    """
    Dataset for drowning detection training
    Expects data structure:
    data/
      ├── videos/
      │   ├── video_001.mp4
      │   ├── video_002.mp4
      │   └── ...
      ├── labels/
      │   ├── video_001.json
      │   ├── video_002.json
      │   └── ...
      └── annotations.json
    """
    
    def __init__(self, data_dir: str, split: str = 'train', sequence_length: int = 90):
        """
        Args:
            data_dir: Root directory containing videos/ and labels/
            split: 'train', 'val', or 'test'
            sequence_length: Number of frames per sequence (default: 90 = 3 seconds at 30fps)
        """
        self.data_dir = Path(data_dir)
        self.split = split
        self.sequence_length = sequence_length
        
        # Load annotations
        annotations_file = self.data_dir / 'annotations.json'
        with open(annotations_file, 'r') as f:
            self.annotations = json.load(f)
        
        # Filter by split
        self.samples = [s for s in self.annotations['samples'] if s['split'] == split]
        
        print(f"Loaded {len(self.samples)} {split} samples")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # Load features (pre-extracted)
        features_file = self.data_dir / 'features' / f"{sample['video_id']}_{sample['track_id']}_{sample['start_frame']}.npy"
        features = np.load(features_file)  # Shape: (sequence_length, 4)
        
        # Load label
        label = sample['label']  # 0=SAFE, 1=WARNING, 2=DANGER
        
        # Load metadata
        metadata = {
            'video_id': sample['video_id'],
            'track_id': sample['track_id'],
            'start_frame': sample['start_frame'],
            'person_size': sample.get('person_size', 'unknown')  # child/adult
        }
        
        return {
            'features': torch.FloatTensor(features),
            'label': torch.LongTensor([label]),
            'metadata': metadata
        }


class PoseDataset(Dataset):
    """
    Dataset for pose estimation fine-tuning
    Uses COCO keypoint format
    """
    
    def __init__(self, images_dir: str, annotations_file: str, img_size: int = 640):
        self.images_dir = Path(images_dir)
        self.img_size = img_size
        
        # Load COCO-format annotations
        with open(annotations_file, 'r') as f:
            self.coco_data = json.load(f)
        
        self.images = self.coco_data['images']
        self.annotations = self.coco_data['annotations']
        
        # Create image_id to annotations mapping
        self.img_to_anns = {}
        for ann in self.annotations:
            img_id = ann['image_id']
            if img_id not in self.img_to_anns:
                self.img_to_anns[img_id] = []
            self.img_to_anns[img_id].append(ann)
    
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, idx):
        img_info = self.images[idx]
        img_path = self.images_dir / img_info['file_name']
        
        # Load image
        img = cv2.imread(str(img_path))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Resize
        img = cv2.resize(img, (self.img_size, self.img_size))
        
        # Get annotations
        img_id = img_info['id']
        anns = self.img_to_anns.get(img_id, [])
        
        return img, anns


def train_lstm_model(
    data_dir: str,
    output_path: str = 'weights/behavior/drowning_lstm.pt',
    num_epochs: int = 50,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
):
    """
    Train LSTM model for drowning risk classification
    
    Args:
        data_dir: Directory containing training data
        output_path: Where to save trained model
        num_epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        device: 'cuda' or 'cpu'
    """
    print("=" * 70)
    print("Training LSTM Drowning Risk Classifier")
    print("=" * 70)
    
    # Create datasets
    train_dataset = DrowningDataset(data_dir, split='train')
    val_dataset = DrowningDataset(data_dir, split='val')
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # Initialize model
    model = TemporalLSTMClassifier(input_size=4, hidden_size=32, output_size=3)
    model = model.to(device)
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5, patience=5, verbose=True
    )
    
    # Training loop
    best_val_acc = 0.0
    
    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch+1}/{num_epochs}")
        print("-" * 70)
        
        # Training phase
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for batch in tqdm(train_loader, desc="Training"):
            features = batch['features'].to(device)
            labels = batch['label'].squeeze().to(device)
            
            optimizer.zero_grad()
            logits, probs = model(features)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = torch.max(probs, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()
        
        train_acc = train_correct / train_total
        avg_train_loss = train_loss / len(train_loader)
        
        # Validation phase
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        # Per-class accuracy
        class_correct = [0, 0, 0]
        class_total = [0, 0, 0]
        
        with torch.no_grad():
            for batch in tqdm(val_loader, desc="Validation"):
                features = batch['features'].to(device)
                labels = batch['label'].squeeze().to(device)
                
                logits, probs = model(features)
                loss = criterion(logits, labels)
                
                val_loss += loss.item()
                _, predicted = torch.max(probs, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
                
                # Per-class accuracy
                for i in range(len(labels)):
                    label = labels[i].item()
                    class_total[label] += 1
                    if predicted[i] == labels[i]:
                        class_correct[label] += 1
        
        val_acc = val_correct / val_total
        avg_val_loss = val_loss / len(val_loader)
        
        # Print metrics
        print(f"\nResults:")
        print(f"  Train Loss: {avg_train_loss:.4f} | Train Acc: {train_acc:.4f}")
        print(f"  Val Loss:   {avg_val_loss:.4f} | Val Acc:   {val_acc:.4f}")
        print(f"\n  Per-class Accuracy:")
        print(f"    SAFE:    {class_correct[0]/max(class_total[0], 1):.4f} ({class_correct[0]}/{class_total[0]})")
        print(f"    WARNING: {class_correct[1]/max(class_total[1], 1):.4f} ({class_correct[1]}/{class_total[1]})")
        print(f"    DANGER:  {class_correct[2]/max(class_total[2], 1):.4f} ({class_correct[2]}/{class_total[2]})")
        
        # Learning rate scheduling
        scheduler.step(val_acc)
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            
            # Save checkpoint
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
                'input_size': 4,
                'hidden_size': 32,
                'output_size': 3,
                'class_accuracies': {
                    'safe': class_correct[0]/max(class_total[0], 1),
                    'warning': class_correct[1]/max(class_total[1], 1),
                    'danger': class_correct[2]/max(class_total[2], 1)
                }
            }, output_path)
            
            print(f"\n  ✅ Saved new best model (val_acc: {val_acc:.4f})")
    
    print("\n" + "=" * 70)
    print(f"Training Complete!")
    print(f"Best Validation Accuracy: {best_val_acc:.4f}")
    print(f"Model saved to: {output_path}")
    print("=" * 70)


def finetune_pose_model(
    data_yaml: str,
    base_model: str = 'yolov8n-pose.pt',
    output_dir: str = 'weights/behavior',
    epochs: int = 100,
    img_size: int = 640,
    batch_size: int = 16,
    device: str = '0' if torch.cuda.is_available() else 'cpu'
):
    """
    Fine-tune YOLOv8-pose model on custom swimming pool data
    
    Args:
        data_yaml: Path to data.yaml file with dataset configuration
        base_model: Base model to fine-tune from
        output_dir: Where to save fine-tuned model
        epochs: Number of training epochs
        img_size: Image size for training
        batch_size: Batch size
        device: Device to train on
    """
    print("=" * 70)
    print("Fine-tuning YOLOv8-Pose Model")
    print("=" * 70)
    
    # Load base model
    model = YOLO(base_model)
    
    # Train
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=img_size,
        batch=batch_size,
        device=device,
        project=output_dir,
        name='yolov8n-pose-finetuned',
        exist_ok=True,
        pretrained=True,
        optimizer='Adam',
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,
        box=7.5,
        cls=0.5,
        dfl=1.5,
        pose=12.0,
        kobj=1.0,
        label_smoothing=0.0,
        nbs=64,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=0.0,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.0,
        copy_paste=0.0,
        save=True,
        save_period=10,
        val=True,
        plots=True
    )
    
    print("\n" + "=" * 70)
    print("Fine-tuning Complete!")
    print(f"Model saved to: {output_dir}/yolov8n-pose-finetuned/weights/best.pt")
    print("=" * 70)
    
    return results


def extract_features_from_videos(
    video_dir: str,
    labels_dir: str,
    output_dir: str,
    pose_model_path: str = 'weights/behavior/yolov8n-pose.pt',
    detection_models: List[str] = ['weights/best.pt', 'weights/best1.pt']
):
    """
    Extract LSTM features from labeled videos
    
    Args:
        video_dir: Directory containing videos
        labels_dir: Directory containing label JSON files
        output_dir: Where to save extracted features
        pose_model_path: Path to pose model
        detection_models: List of detection model paths for ensemble
    """
    print("=" * 70)
    print("Extracting Features from Videos")
    print("=" * 70)
    
    from core.person_classifier import EnsembleDetector
    
    # Initialize models
    ensemble_detector = EnsembleDetector(detection_models)
    pose_detector = PoseDetector(model_path=pose_model_path, device='cpu')
    feature_extractor = BehaviorFeatureExtractor()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Process each video
    video_files = list(Path(video_dir).glob('*.mp4'))
    
    for video_file in tqdm(video_files, desc="Processing videos"):
        video_id = video_file.stem
        label_file = Path(labels_dir) / f"{video_id}.json"
        
        if not label_file.exists():
            print(f"  ⚠️  No labels for {video_id}, skipping")
            continue
        
        # Load labels
        with open(label_file, 'r') as f:
            labels = json.load(f)
        
        # Open video
        cap = cv2.VideoCapture(str(video_file))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        
        # Track buffers
        track_features = {}
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect persons
            detections = ensemble_detector.detect(frame)
            
            # Detect poses
            bboxes = [d['bbox'] for d in detections]
            poses = pose_detector.detect_poses(frame, bboxes)
            
            # Extract features for each detection
            for detection, pose in zip(detections, poses):
                if not pose['available']:
                    continue
                
                # Find matching track in labels
                track_id = None
                for seq in labels['sequences']:
                    if seq['start_frame'] <= frame_idx <= seq['end_frame']:
                        # Simple matching by IoU (in real scenario, use proper tracking)
                        track_id = seq['track_id']
                        break
                
                if track_id is None:
                    continue
                
                # Extract features
                features = feature_extractor.extract(
                    pose['keypoints'],
                    detection['bbox'],
                    frame_height,
                    track_id
                )
                
                # Add to buffer
                if track_id not in track_features:
                    track_features[track_id] = {
                        'features': [],
                        'label': None,
                        'person_size': None
                    }
                
                track_features[track_id]['features'].append(features)
            
            frame_idx += 1
        
        cap.release()
        
        # Save feature sequences
        for track_id, data in track_features.items():
            features_array = np.array(data['features'])
            
            # Create 90-frame sequences
            for i in range(0, len(features_array) - 90, 30):  # Stride of 30 frames
                sequence = features_array[i:i+90]
                
                # Find label for this sequence
                mid_frame = i + 45
                label = 0  # Default SAFE
                person_size = 'unknown'
                
                for seq in labels['sequences']:
                    if seq['track_id'] == track_id and seq['start_frame'] <= mid_frame <= seq['end_frame']:
                        label = seq['label']
                        person_size = seq.get('person_size', 'unknown')
                        break
                
                # Save
                output_file = output_path / f"{video_id}_{track_id}_{i}.npy"
                np.save(output_file, sequence)
                
                # Save metadata
                metadata_file = output_path / f"{video_id}_{track_id}_{i}.json"
                with open(metadata_file, 'w') as f:
                    json.dump({
                        'video_id': video_id,
                        'track_id': track_id,
                        'start_frame': i,
                        'label': label,
                        'person_size': person_size
                    }, f)
        
        print(f"  ✅ Processed {video_id}: {len(track_features)} tracks")
    
    print("\n" + "=" * 70)
    print("Feature Extraction Complete!")
    print(f"Features saved to: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Train Drowning Detection Models')
    parser.add_argument('--task', type=str, required=True,
                       choices=['extract', 'train-lstm', 'finetune-pose', 'all'],
                       help='Training task to perform')
    parser.add_argument('--data-dir', type=str, default='data/drowning',
                       help='Data directory')
    parser.add_argument('--epochs', type=int, default=50,
                       help='Number of epochs')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='Batch size')
    
    args = parser.parse_args()
    
    if args.task == 'extract' or args.task == 'all':
        extract_features_from_videos(
            video_dir=f"{args.data_dir}/videos",
            labels_dir=f"{args.data_dir}/labels",
            output_dir=f"{args.data_dir}/features"
        )
    
    if args.task == 'train-lstm' or args.task == 'all':
        train_lstm_model(
            data_dir=args.data_dir,
            num_epochs=args.epochs,
            batch_size=args.batch_size
        )
    
    if args.task == 'finetune-pose' or args.task == 'all':
        finetune_pose_model(
            data_yaml=f"{args.data_dir}/data.yaml",
            epochs=args.epochs,
            batch_size=args.batch_size
        )
    
    print("\n✅ All training tasks complete!")
