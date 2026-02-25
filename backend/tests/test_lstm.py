"""
Quick test script to verify LSTM integration
"""

import sys
sys.path.insert(0, '.')

from core.behavior.temporal_model import TemporalLSTMClassifier, create_dummy_model
from core.behavior.behavior_features import BehaviorFeatureExtractor
from core.behavior.inference import RiskInferenceEngine
import torch
import numpy as np
from pathlib import Path

print("=" * 60)
print("LSTM Integration Test")
print("=" * 60)

# Test 1: LSTM Model
print("\n1. Testing LSTM Model...")
try:
    model = TemporalLSTMClassifier(input_size=4, hidden_size=32, output_size=3)
    print("   ✅ LSTM model created")
    print(f"   - Input size: 4")
    print(f"   - Hidden size: 32")
    print(f"   - Output size: 3")
    
    # Test forward pass
    dummy_input = torch.randn(1, 90, 4)  # (batch, sequence, features)
    logits, probs = model(dummy_input)
    print(f"   ✅ Forward pass successful")
    print(f"   - Output shape: {probs.shape}")
    print(f"   - Probabilities: {probs[0].tolist()}")
except Exception as e:
    print(f"   ❌ LSTM model test failed: {e}")

# Test 2: Dummy Model Creation
print("\n2. Testing Dummy Model Creation...")
try:
    dummy_path = Path("weights/behavior/test_dummy.pt")
    create_dummy_model(dummy_path)
    print(f"   ✅ Dummy model created at {dummy_path}")
    
    # Load and test
    checkpoint = torch.load(dummy_path, map_location='cpu')
    print(f"   ✅ Dummy model loaded")
    print(f"   - Keys: {list(checkpoint.keys())}")
except Exception as e:
    print(f"   ❌ Dummy model test failed: {e}")

# Test 3: Feature Extractor
print("\n3. Testing Feature Extractor...")
try:
    extractor = BehaviorFeatureExtractor()
    print("   ✅ Feature extractor created")
    
    # Create dummy keypoints (17, 3)
    dummy_keypoints = np.random.rand(17, 3)
    dummy_keypoints[:, 2] = 0.9  # High confidence
    
    dummy_bbox = (100, 200, 300, 400)
    frame_height = 1080
    
    features = extractor.extract(dummy_keypoints, dummy_bbox, frame_height, track_id=1)
    print(f"   ✅ Features extracted")
    print(f"   - Features: {features}")
except Exception as e:
    print(f"   ❌ Feature extractor test failed: {e}")

# Test 4: Risk Inference Engine
print("\n4. Testing Risk Inference Engine...")
try:
    # Create dummy model if not exists
    lstm_path = Path("weights/behavior/drowning_lstm.pt")
    if not lstm_path.exists():
        create_dummy_model(lstm_path)
    
    engine = RiskInferenceEngine(
        model_path=str(lstm_path),
        buffer_size=90,
        min_frames=30,
        device='cpu'
    )
    print(f"   ✅ Risk inference engine created")
    print(f"   - Model available: {engine.is_available()}")
    
    # Test processing
    for i in range(35):  # Add 35 frames to exceed min_frames
        dummy_keypoints = np.random.rand(17, 3)
        dummy_keypoints[:, 2] = 0.9
        dummy_bbox = (100, 200, 300, 400)
        
        result = engine.process_track(
            track_id=1,
            keypoints=dummy_keypoints,
            bbox=dummy_bbox,
            frame_height=1080,
            frame_number=i
        )
    
    print(f"   ✅ Risk inference successful")
    print(f"   - Risk state: {result['risk_state']}")
    print(f"   - Risk scores: {result['risk_scores']}")
    print(f"   - Confidence: {result['confidence']}")
    print(f"   - Buffer size: {result['buffer_size']}")
    print(f"   - Inference ready: {result['inference_ready']}")
    
except Exception as e:
    print(f"   ❌ Risk inference test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)
