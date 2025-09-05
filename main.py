# main.py
import time 

from audio.recorder import AudioRecorder
from audio.wake_word import WakeWordDetector  
from processing_unit.speech_to_text import SpeechToText

def main():
    # Initialize components
    recorder = AudioRecorder()
    wake_word = WakeWordDetector(['alexa'])
    stt = SpeechToText(model_size="base")
    
    print("\nR2-D2 Bot starting... Say 'Alexa' to activate")
    
    try:
        recorder.start_listening()
        last_detection_time = 0
        cooldown_period = 5.0  # 3 second cooldown
       
        while True:
            # Listen for wake word
            audio_chunk = recorder.read_chunk()
            current_time = time.time()
           
           # Only check for wake word if cooldown period has passed
            if (current_time - last_detection_time) > cooldown_period and wake_word.detect(audio_chunk):
                print("Wake word detected! Listening for command...")
                last_detection_time = current_time

                # Record 3s of speech
                command_audio = recorder.record_command(timeout_seconds=2.0)
                
                text = stt.transcribe(command_audio)
                print("Transcription complete...")
                
                # Clear audio buffer and reset wake word model
                print("Clearing buffer and resetting model...")
                recorder.clear_buffer()
                wake_word.reset()
                        
                if text:
                   print(f"You said: {text}")
                   # TODO: Add emotion classification and R2 response
                else:
                    print("No speech detected.")
                
                print("Listening for wake word again...\n")
                continue
               
               
    except KeyboardInterrupt:
        print("\nShutting down R2-D2 Bot...")
    finally:
        recorder.stop_listening()

if __name__ == "__main__":
   main()
               

if __name__ == "__main__":
    main()