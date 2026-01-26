# main.py
import time 
import argparse
from dotenv import load_dotenv
load_dotenv()

from audio.recorder import AudioRecorder, AudioSpeaker
from audio.wake_word import WakeWordDetector  

def main():
    parser = argparse.ArgumentParser(description="R2-D2 Voice System")
    parser.add_argument('--local', action='store_true', help="Use local GPU (Ollama) instead of Groq API")
    args = parser.parse_args()

    # Initialize components
    recorder = AudioRecorder()  
    # r2_model_path = "audio/wakeword_models/heyr2.tflite"
    r2_model_path = "audio/wakeword_models/heyr2.onnx"
    wake_word = WakeWordDetector([r2_model_path], detection_threshold=0.7)
    speaker = AudioSpeaker()

    if args.local:
        from processing_unit.speech_to_text import SpeechToText
        from processing_unit.emotion_response_llm import EmotionClassifier
        stt = SpeechToText(model_size="base")
        emotion_llm = EmotionClassifier()
        print("\nR2-D2 is listening (LOCAL)... Say 'Hey R2' to activate")
    else:
        from processing_unit.emotion_response_llm import EmotionClassifier_API
        processor = EmotionClassifier_API()
        print("\nR2-D2 is listening (API)... Say 'Hey R2' to activate")
    
    try:
        recorder.start_listening()
        last_detection_time = 0
        cooldown_period = 5.0  # 5 second cooldown
       
        while True:
            # Listen for wake word
            audio_chunk = recorder.read_chunk()
            current_time = time.time()
           
           # Only check for wake word if cooldown period has passed
            if (current_time - last_detection_time) > cooldown_period and wake_word.detect(audio_chunk):
                print("'Hey R2' Wake word detected! Listening for command...")
                last_detection_time = current_time

                # Record 3s of speech
                command_audio = recorder.record_command(timeout_seconds=3.0)
                
                # Transcribe and classify
                if args.local:
                    input_text = stt.transcribe(command_audio)
                    emotion = emotion_llm.classify(input_text) if input_text else None
                else:
                    input_text, emotion = processor.process_audio(command_audio)
                
                # Clear audio buffer and reset wake word model for next listen
                recorder.clear_buffer()
                wake_word.reset()
                        
                if input_text:
                   print(f"Transcription: {input_text}")
                   print(f"Emotion: {emotion}")
                   
                   # Select and play the appropriate sound
                   speaker.speak(emotion)
                   
                else:
                    print("No speech detected.")
                
                print("\nListening for wake word again...\n")
                continue
               
               
    except KeyboardInterrupt:
        print("\nShutting down R2-D2 Bot...")
    finally:
        recorder.stop_listening()
        exit()

if __name__ == "__main__":
   main()