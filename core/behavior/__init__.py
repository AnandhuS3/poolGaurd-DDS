"""
Behavior Analysis Module - LSTM-based Temporal Classification
Provides deterministic feature extraction and neural temporal inference
"""

from .behavior_features import BehaviorFeatureExtractor
from .temporal_model import TemporalLSTMClassifier
from .inference import RiskInferenceEngine

__all__ = ['BehaviorFeatureExtractor', 'TemporalLSTMClassifier', 'RiskInferenceEngine']
