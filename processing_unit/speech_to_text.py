# processing_unit/speech_to_text.py
import whisper
import io
import wave
import tempfile
import os
import argparse

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


class SpeechToText_API:
    """Cloud speech-to-text using Groq Whisper API"""
    def __init__(self, api_key: str = None):
        """
        Initialize Groq client.
        If api_key is None, uses GROQ_API_KEY environment variable.
        """
        from groq import Groq
        from dotenv import load_dotenv
        load_dotenv()

        self.client = Groq(api_key=api_key)

    def transcribe(self, audio_data: bytes) -> str:
        """Convert audio bytes to text using Groq Whisper"""
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "audio.wav"

        transcription = self.client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_file
        )
        return transcription.text.strip()


def main():
    import sys
    import os
    # Add project root to path for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    parser = argparse.ArgumentParser(description="R2-D2 Speech-to-Text Test")
    parser.add_argument('--local', action='store_true', help="Use local Whisper instead of Groq API")
    args = parser.parse_args()

    from audio.recorder import AudioRecorder

    if args.local:
        print("R2-D2 Speech-to-Text Test (Local Whisper)")
        stt = SpeechToText(model_size="base")
    else:
        print("R2-D2 Speech-to-Text Test (Groq API)")
        print("Using GROQ_API_KEY environment variable")
        stt = SpeechToText_API()

    recorder = AudioRecorder()

    try:
        recorder.start_listening()
        print("\nRecording for 3 seconds...")
        audio_data = recorder.record_command(timeout_seconds=2.0)

        print("Transcribing...")
        text = stt.transcribe(audio_data)
        print(f"Transcription: {text}")
    finally:
        recorder.stop_listening()


if __name__ == "__main__":
    main()