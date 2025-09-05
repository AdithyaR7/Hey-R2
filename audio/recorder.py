# audio/recorder.py
import pyaudio
import numpy as np
import wave
import io
from typing import Optional

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
