"""
State Machine - Enhanced state transitions with behavior context
"""

from enum import Enum
from typing import Dict, Optional
import logging
from .behavior_patterns import BehaviorType

logger = logging.getLogger(__name__)


class PersonState(Enum):
    """Enhanced person states"""
    SAFE = "SAFE"
    ATTENTION = "ATTENTION"  # New: Unusual behavior detected
    WARNING = "WARNING"
    DANGER = "DANGER"


class StateMachine:
    """
    Enhanced state machine with behavior-aware transitions
    Reduces false positives by requiring sustained abnormal behavior
    """
    
    def __init__(self, attention_threshold: int = 15, 
                 warning_threshold: int = 30, 
                 danger_threshold: int = 60):
        """
        Initialize state machine
        
        Args:
            attention_threshold: Frames before ATTENTION state
            warning_threshold: Frames before WARNING state
            danger_threshold: Frames before DANGER state
        """
        self.attention_threshold = attention_threshold
        self.warning_threshold = warning_threshold
        self.danger_threshold = danger_threshold
        
        # Track state for each person
        self.person_states: Dict[int, Dict] = {}
    
    def update(self, track_id: int, behavior: BehaviorType, 
               frame_number: int) -> PersonState:
        """
        Update state based on current behavior
        
        Args:
            track_id: Person tracking ID
            behavior: Current classified behavior
            frame_number: Current frame number
        
        Returns:
            Updated PersonState
        """
        # Initialize if new person
        if track_id not in self.person_states:
            self.person_states[track_id] = {
                'state': PersonState.SAFE,
                'behavior_history': [],
                'attention_start_frame': None,
                'warning_start_frame': None,
                'danger_start_frame': None,
                'frames_in_state': 0,
                'previous_state': PersonState.SAFE
            }
        
        person = self.person_states[track_id]
        current_state = person['state']
        
        # Add behavior to history (keep last 10)
        person['behavior_history'].append(behavior)
        if len(person['behavior_history']) > 10:
            person['behavior_history'].pop(0)
        
        # Determine new state based on behavior
        new_state = self._determine_state(track_id, behavior, frame_number)
        
        # Update state if changed
        if new_state != current_state:
            logger.info(f"[STATE CHANGE] Person #{track_id}: {current_state.value} → {new_state.value} (behavior: {behavior.value})")
            person['previous_state'] = current_state
            person['state'] = new_state
            person['frames_in_state'] = 0
        else:
            person['frames_in_state'] += 1
        
        return new_state
    
    def _determine_state(self, track_id: int, behavior: BehaviorType, 
                        frame_number: int) -> PersonState:
        """
        Determine state based on behavior and thresholds
        
        State Transition Logic:
        - SAFE → ATTENTION: Unusual behavior (STRUGGLING)
        - ATTENTION → WARNING: Sustained struggling
        - WARNING → DANGER: DROWNING behavior detected
        - DANGER → WARNING: Improvement (requires manual review)
        - WARNING → SAFE: Normal behavior sustained
        - ATTENTION → SAFE: Normal behavior sustained
        """
        person = self.person_states[track_id]
        current_state = person['state']
        
        # DANGER state is sticky (requires manual intervention)
        if current_state == PersonState.DANGER:
            # Only allow downgrade if behavior improves significantly
            if behavior in [BehaviorType.SWIMMING, BehaviorType.FLOATING]:
                if person['frames_in_state'] > 30:  # Must improve for 30 frames
                    return PersonState.WARNING
            return PersonState.DANGER
        
        # Check for DROWNING behavior (immediate DANGER)
        if behavior == BehaviorType.DROWNING:
            if person['danger_start_frame'] is None:
                person['danger_start_frame'] = frame_number
            
            frames_drowning = frame_number - person['danger_start_frame']
            if frames_drowning >= self.danger_threshold:
                return PersonState.DANGER
            elif frames_drowning >= self.warning_threshold:
                return PersonState.WARNING
            else:
                return PersonState.ATTENTION
        else:
            person['danger_start_frame'] = None
        
        # Check for STRUGGLING behavior
        if behavior == BehaviorType.STRUGGLING:
            if person['warning_start_frame'] is None:
                person['warning_start_frame'] = frame_number
            
            frames_struggling = frame_number - person['warning_start_frame']
            if frames_struggling >= self.warning_threshold:
                return PersonState.WARNING
            elif frames_struggling >= self.attention_threshold:
                return PersonState.ATTENTION
            else:
                return current_state  # Stay in current state
        else:
            person['warning_start_frame'] = None
        
        # Normal behaviors (SWIMMING, DIVING, FLOATING)
        if behavior in [BehaviorType.SWIMMING, BehaviorType.DIVING, BehaviorType.FLOATING]:
            # Recovery logic
            if current_state == PersonState.WARNING:
                # Require sustained normal behavior to recover
                if person['frames_in_state'] >= 45:  # 1.5 seconds
                    return PersonState.SAFE
                return PersonState.WARNING
            
            elif current_state == PersonState.ATTENTION:
                if person['frames_in_state'] >= 30:  # 1 second
                    return PersonState.SAFE
                return PersonState.ATTENTION
            
            else:
                return PersonState.SAFE
        
        # UNKNOWN behavior - maintain current state
        return current_state
    
    def get_state(self, track_id: int) -> PersonState:
        """Get current state for a person"""
        if track_id not in self.person_states:
            return PersonState.SAFE
        return self.person_states[track_id]['state']
    
    def get_state_info(self, track_id: int) -> Optional[Dict]:
        """Get detailed state information"""
        if track_id not in self.person_states:
            return None
        
        person = self.person_states[track_id]
        return {
            'state': person['state'].value,
            'previous_state': person['previous_state'].value,
            'frames_in_state': person['frames_in_state'],
            'recent_behaviors': [b.value for b in person['behavior_history'][-5:]],
            'attention_active': person['attention_start_frame'] is not None,
            'warning_active': person['warning_start_frame'] is not None,
            'danger_active': person['danger_start_frame'] is not None
        }
    
    def reset_person(self, track_id: int):
        """Reset state for a person"""
        if track_id in self.person_states:
            del self.person_states[track_id]
    
    def reset_all(self):
        """Reset all person states"""
        self.person_states.clear()
