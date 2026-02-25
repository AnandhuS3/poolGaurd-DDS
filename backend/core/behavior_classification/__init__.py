"""
Behavior Classification Module
Provides temporal analysis and behavior classification for drowning detection
"""

from .temporal_buffer import TemporalBuffer
from .behavior_classifier import BehaviorClassifier
from .behavior_patterns import BehaviorPattern, BehaviorType
from .state_machine import StateMachine, PersonState

__all__ = [
    'TemporalBuffer',
    'BehaviorClassifier',
    'BehaviorPattern',
    'BehaviorType',
    'StateMachine',
    'PersonState'
]
