# processing_unit/speech_to_text.py
import whisper
import io
import wave
import tempfile
import os

class SpeechToText:
    def __init__(self, model_size: str = "base"):
        """Initialize Whisper model
        Args:
            model_size: tiny, base, small, medium, large
        """
        print(f"\nLoading Whisper {model_size} model...")
        self.model = whisper.load_model(model_size)
        
    def transcribe(self, audio_data: bytes) -> str:
        """Convert audio bytes to text"""
        # Write audio data to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        try:
            # Transcribe using Whisper
            result = self.model.transcribe(temp_path)
            text = result["text"].strip()
            # print(f"Transcribed: '{text}'")
            return text
        finally:
            # Clean up temp file
            os.unlink(temp_path)