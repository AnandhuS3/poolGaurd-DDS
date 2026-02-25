"""
Temporal LSTM Classifier - Lightweight neural network for drowning detection
Input: 4 features (vertical_ratio, arm_velocity, horizontal_displacement, head_oscillation)
Hidden: 32 LSTM units
Output: 3 classes (SAFE, WARNING, DANGER)
"""

import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TemporalLSTMClassifier(nn.Module):
    """
    Lightweight LSTM for temporal behavior classification
    
    Architecture:
    - Input: (batch, sequence_length, 4) features
    - LSTM: 4 -> 32 hidden units
    - Output: 32 -> 3 classes (SAFE, WARNING, DANGER)
    """
    
    def __init__(self, input_size: int = 4, hidden_size: int = 32, output_size: int = 3):
        """
        Initialize LSTM classifier
        
        Args:
            input_size: Number of input features (default: 4)
            hidden_size: LSTM hidden units (default: 32)
            output_size: Number of output classes (default: 3)
        """
        super(TemporalLSTMClassifier, self).__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        # LSTM layer
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True
        )
        
        # Fully connected output layer
        self.fc = nn.Linear(hidden_size, output_size)
        
        # Softmax for probabilities
        self.softmax = nn.Softmax(dim=1)
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass
        
        Args:
            x: Input tensor (batch, sequence_length, 4)
        
        Returns:
            logits: Raw output (batch, 3)
            probs: Softmax probabilities (batch, 3)
        """
        # LSTM forward
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # Use last hidden state
        last_hidden = h_n[-1]  # (batch, hidden_size)
        
        # Fully connected layer
        logits = self.fc(last_hidden)  # (batch, 3)
        
        # Softmax probabilities
        probs = self.softmax(logits)
        
        return logits, probs
    
    def predict(self, x: torch.Tensor) -> Tuple[int, np.ndarray]:
        """
        Predict class and probabilities
        
        Args:
            x: Input tensor (1, sequence_length, 4) or (sequence_length, 4)
        
        Returns:
            predicted_class: 0=SAFE, 1=WARNING, 2=DANGER
            probabilities: (3,) array of class probabilities
        """
        # Ensure batch dimension
        if x.dim() == 2:
            x = x.unsqueeze(0)  # Add batch dimension
        
        # Forward pass
        with torch.no_grad():
            _, probs = self.forward(x)
        
        # Get predicted class
        predicted_class = torch.argmax(probs, dim=1).item()
        
        # Convert probabilities to numpy
        probs_np = probs.cpu().numpy()[0]
        
        return predicted_class, probs_np


class LSTMModelLoader:
    """
    Loads and manages LSTM model from weights file
    """
    
    def __init__(self, model_path: Optional[Path] = None, device: str = 'cpu'):
        """
        Initialize model loader
        
        Args:
            model_path: Path to model weights (.pt file)
            device: 'cpu' or 'cuda'
        """
        self.model_path = model_path
        self.device = device
        self.model = None
        self.loaded = False
    
    def load(self) -> bool:
        """
        Load model from weights file
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if self.model_path is None or not Path(self.model_path).exists():
            logger.warning(f"Model weights not found: {self.model_path}")
            return False
        
        try:
            # Initialize model
            self.model = TemporalLSTMClassifier(
                input_size=4,
                hidden_size=32,
                output_size=3
            )
            
            # Load weights
            checkpoint = torch.load(self.model_path, map_location=self.device)
            
            # Handle different checkpoint formats
            if isinstance(checkpoint, dict):
                if 'model_state_dict' in checkpoint:
                    self.model.load_state_dict(checkpoint['model_state_dict'])
                elif 'state_dict' in checkpoint:
                    self.model.load_state_dict(checkpoint['state_dict'])
                else:
                    self.model.load_state_dict(checkpoint)
            else:
                self.model.load_state_dict(checkpoint)
            
            # Set to evaluation mode
            self.model.eval()
            self.model.to(self.device)
            
            self.loaded = True
            logger.info(f"✅ LSTM model loaded from {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load LSTM model: {e}")
            self.loaded = False
            return False
    
    def get_model(self) -> Optional[TemporalLSTMClassifier]:
        """Get loaded model"""
        if not self.loaded:
            return None
        return self.model
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.loaded


def create_dummy_model(save_path: Path):
    """
    Create a dummy LSTM model for testing (when real weights not available)
    
    Args:
        save_path: Path to save dummy model
    """
    logger.info("Creating dummy LSTM model for testing...")
    
    # Initialize model
    model = TemporalLSTMClassifier(input_size=4, hidden_size=32, output_size=3)
    
    # Initialize with reasonable weights
    # (In production, this would be trained on real drowning data)
    with torch.no_grad():
        # Bias towards SAFE class for safety
        model.fc.bias[0] = 1.0  # SAFE
        model.fc.bias[1] = 0.0  # WARNING
        model.fc.bias[2] = -1.0  # DANGER
    
    # Save model
    save_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'model_state_dict': model.state_dict(),
        'input_size': 4,
        'hidden_size': 32,
        'output_size': 3,
        'note': 'Dummy model for testing - replace with trained model'
    }, save_path)
    
    logger.info(f"✅ Dummy LSTM model saved to {save_path}")
    logger.warning("⚠️  This is a DUMMY model - replace with trained weights for production!")
