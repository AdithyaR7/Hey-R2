# audio/recorder.py
import pyaudio
import wave
import io
from typing import Optional
import pygame
import random
import os

class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        
    def start_listening(self):
        """Start the audio input stream"""
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
    
    def read_chunk(self) -> bytes:
        """Read a single audio chunk"""
        if not self.stream:
            raise RuntimeError("Audio stream not started")
        return self.stream.read(self.chunk_size)
    
    def record_command(self, timeout_seconds: float = 3.0) -> bytes:
        """Record audio for a fixed duration"""
        if not self.stream:
            raise RuntimeError("Audio stream not started")
            
        frames = []
        num_chunks = int(self.sample_rate / self.chunk_size * timeout_seconds)
        
        for _ in range(num_chunks):
            data = self.stream.read(self.chunk_size)
            frames.append(data)
        
        # Convert to WAV format in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(b''.join(frames))
        
        wav_buffer.seek(0)
        return wav_buffer.read()
    
    def clear_buffer(self):
        """Clear all pending audio data from the input buffer"""
        if not self.stream:
            return
        
        # Read available data to clear buffer
        try:
            # Check how much data is available
            available_frames = self.stream.get_read_available()
            if available_frames > 0:
                # Read all available frames
                self.stream.read(available_frames, exception_on_overflow=False)
        except Exception:
            # Fallback: try to read a few chunks to clear buffer
            try:
                for _ in range(10):  # Read up to 10 chunks
                    self.stream.read(self.chunk_size, exception_on_overflow=False)
            except Exception:
                pass
    
    def stop_listening(self):
        """Stop and clean up audio stream"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()


class AudioSpeaker:
    def __init__(self):
        """Initialize pygame mixer for audio playback"""
        pygame.mixer.init()
    
    def speak(self, emotion: str):
        """Play a random R2-D2 sound file from the emotion category folder"""
        sound_folder = f"audio/sounds/{emotion}"
        
        try:
            # Get all audio files in the emotion folder
            if not os.path.exists(sound_folder):
                print(f"Sound folder not found: {sound_folder}")
                return
            
            audio_files = [f for f in os.listdir(sound_folder) 
                          if f.lower().endswith(('.wav', '.mp3', '.ogg'))]
            
            if not audio_files:
                print(f"No audio files found in {sound_folder}")
                return
            
            # Pick random audio file
            selected_file = random.choice(audio_files)
            file_path = os.path.join(sound_folder, selected_file)
            
            # print(f"Playing R2-D2 sound: {selected_file}")
            
            # Load and play the sound
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # Wait for sound to finish
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                
        except Exception as e:
            print(f"Error playing sound: {e}")
            

def main():
    """Test the AudioSpeaker functionality"""
    print("R2-D2 Audio Speaker Test")
    print("Available emotions: happy, curious, concerned, scared, acknowledge")
    print("Type 'quit' to exit\n")
    
    speaker = AudioSpeaker()
    
    while True:
        emotion = input("Enter emotion to play: ").strip().lower()
        
        if emotion == 'quit':
            break
        
        valid_emotions = ['happy', 'curious', 'concerned', 'scared', 'acknowledge']
        
        if emotion in valid_emotions:
            speaker.speak(emotion)
        else:
            print(f"Invalid emotion. Choose from: {', '.join(valid_emotions)}")
        
        print()

if __name__ == "__main__":
    main()