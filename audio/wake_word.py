# audio/wake_word.py
import openwakeword
from openwakeword import Model
import numpy as np

class WakeWordDetector:
    def __init__(self, wakeword_models: list = None):
        if wakeword_models is None:
            wakeword_models = ['alexa']  # Default to alexa for testing
        
        self.model = Model(wakeword_models=wakeword_models)
        self.threshold = 0.5
        
    def detect(self, audio_chunk: bytes) -> bool:
        """Check if wake word is detected in audio chunk"""
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32)
        
        # Get predictions
        predictions = self.model.predict(audio_array)
        
        # Check if any wake word exceeds threshold
        for wake_word, confidence in predictions.items():
            if confidence > self.threshold:
                print(f"Wake word '{wake_word}' detected with confidence {confidence:.2f}")
                return True
        
        return False
    
    def set_threshold(self, threshold: float):
        """Adjust detection sensitivity"""
        self.threshold = threshold
    
    def reset(self):
        """Reset the wake word model state to clear internal audio buffers"""
        self.model.reset()