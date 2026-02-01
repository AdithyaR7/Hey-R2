#!/usr/bin/env python3
import sys
import time
import argparse
import threading

sys.path.append('pi_cam')
sys.path.append('hardware')

from audio.recorder import AudioRecorder, AudioSpeaker
from audio.wake_word import WakeWordDetector

# ============================================================================
# STATE MANAGEMENT
# ============================================================================

class StateManager:
    """Thread-safe state management using flags"""
    def __init__(self):
        self._lock = threading.Lock()

        # Tracking subsystem
        self.tracking_enabled = True  # Default ON

        # HeyR2 subsystem
        self.audio_enabled = True     # Default ON

        # System
        self.shutdown_event = threading.Event()

    def is_tracking_enabled(self):
        with self._lock:
            return self.tracking_enabled

    def is_audio_enabled(self):
        with self._lock:
            return self.audio_enabled

    def should_shutdown(self):
        return self.shutdown_event.is_set()

    def request_shutdown(self):
        self.shutdown_event.set()

# ============================================================================
# TRACKING SUBSYSTEM
# ============================================================================

def tracking_loop(state_manager: StateManager, args):
    """Runs the visual tracking system"""

    # Initialize camera and motor based on mode
    if args.cpu:
        from cpu_camera import Camera
        from motor import Motor
        camera = Camera(model_name='pi_cam/weights/yolo26n.pt', resolution=(640, 480), fps=30, flip=True, debug=args.debug_tracking)
        motor = Motor(servo_pin=12, debug=args.debug_tracking)
        use_threaded = False
    else:
        from hailo_camera import HailoCamera
        from motor_threaded import Motor
        camera = HailoCamera(model_path='pi_cam/weights/yolov6n_h8l.hef', flip=True, debug=args.debug_tracking)
        motor = Motor(servo_pin=12, debug=args.debug_tracking)
        use_threaded = True

    print(f"[TRACKER] Mode: {'CPU' if args.cpu else 'Hailo'}")
    print(f"[TRACKER] Motor: {'Threaded' if use_threaded else 'Direct PID'}")

    motor.move_home()
    if args.debug_tracking:
        print("[TRACKER] Motor initialized to home - 90 degrees")
    time.sleep(2)

    if use_threaded:
        motor.start_control_loop()

    fps_counter = 0
    fps_timer = time.time()
    tracking_active = False

    try:
        while not state_manager.should_shutdown():
            # Check if tracking is enabled (allows disabling via voice commands later)
            if not state_manager.is_tracking_enabled():
                time.sleep(0.1)
                continue

            offset, confidence = camera.get_person_offset()

            if offset is not None:
                if not tracking_active:
                    if args.debug_tracking:
                        print(f"[TRACKER] Target acquired! Confidence: {confidence:.2f}")
                    tracking_active = True

                if use_threaded:
                    motor.set_target_from_offset(offset)
                else:
                    moved = motor.move_by_offset_pid(offset)
                    if not moved and args.debug_tracking:
                        print("[TRACKER] Centered - minimal movement")
            else:
                if use_threaded:
                    if tracking_active and args.debug_tracking:
                        print("[TRACKER] Target lost")
                    tracking_active = False
                else:
                    motor.pid.reset()
                    if tracking_active:
                        if args.debug_tracking:
                            print("[TRACKER] Target lost")
                        motor.stop()
                        tracking_active = False

            if camera.check_quit():
                state_manager.request_shutdown()
                break

            # FPS monitoring
            fps_counter += 1
            if time.time() - fps_timer >= 3.0:
                fps = fps_counter / 3.0
                if args.debug_tracking:
                    if use_threaded:
                        print(f"[TRACKER] Detection FPS: {fps:.1f} | Motor: 100 Hz")
                    else:
                        print(f"[TRACKER] Tracking FPS: {fps:.1f}")
                fps_counter = 0
                fps_timer = time.time()

    finally:
        # Cleanup
        if use_threaded:
            if args.debug_tracking:
                print("[TRACKER] Stopping motor control loop...")
            motor.stop_control_loop()
            time.sleep(0.5)
        else:
            time.sleep(1)

        if args.debug_tracking:
            print("[TRACKER] Returning home...")
        motor.move_home()
        if args.debug_tracking:
            print("[TRACKER] Cleaning up...")
        camera.cleanup()
        motor.cleanup()
        print("[TRACKER] Stopped")

# ============================================================================
# HEYR2 SUBSYSTEM
# ============================================================================

def process_command(command_text, state_manager: StateManager, speaker: AudioSpeaker, args):
    """
    Process voice commands and update state accordingly

    Returns:
        bool: True if command was handled (skip emotion LLM), False otherwise (continue to emotion response)

    TODO: Add command handling here:
    - "mute" -> state_manager.audio_enabled = False
    - "track me" -> state_manager.tracking_enabled = True
    - "stop tracking" -> state_manager.tracking_enabled = False
    - etc.
    """
    command_lower = command_text.lower()

    if args.debug_heyr2:
        print(f"[AUDIO] Processing command: '{command_text}'")

    # TODO: Command parsing will go here
    # Example:
    # if "mute" in command_lower:
    #     with state_manager._lock:
    #         state_manager.audio_enabled = False
    #     print("[AUDIO] Audio muted")
    #     return True  # Command handled, skip emotion
    #
    # if "track" in command_lower:
    #     with state_manager._lock:
    #         state_manager.tracking_enabled = True
    #     print("[AUDIO] Tracking enabled")
    #     return True

    # Not a system command - continue to emotion response
    return False

def audio_loop(state_manager: StateManager, args):
    """Runs the audio interaction system"""

    # Initialize audio components
    recorder = AudioRecorder()
    r2_model_path = "audio/wakeword_models/heyr2.onnx"
    wake_word = WakeWordDetector([r2_model_path], detection_threshold=0.7)
    speaker = AudioSpeaker()

    # Initialize STT and emotion classifier
    if args.local:
        from processing_unit.speech_to_text import SpeechToText
        from processing_unit.emotion_response_llm import EmotionClassifier
        stt = SpeechToText(model_size="base")
        emotion_llm = EmotionClassifier()
        print("[AUDIO] Mode: LOCAL (Ollama)")
    else:
        from processing_unit.speech_to_text import SpeechToText_API
        from processing_unit.emotion_response_llm import EmotionClassifier_API
        stt = SpeechToText_API()
        emotion_llm = EmotionClassifier_API()
        print("[AUDIO] Mode: API (Groq)")

    recorder.start_listening()
    last_detection_time = 0
    cooldown_period = 5.0

    print("[AUDIO] Listening for 'Hey R2'...")

    try:
        while not state_manager.should_shutdown():
            # Check if audio is enabled
            if not state_manager.is_audio_enabled():
                time.sleep(0.1)
                continue

            # Listen for wake word
            audio_chunk = recorder.read_chunk()
            current_time = time.time()

            if (current_time - last_detection_time) > cooldown_period and wake_word.detect(audio_chunk):
                print("[AUDIO] 'Hey R2' detected! Listening for command...")
                last_detection_time = current_time

                # Record command
                command_audio = recorder.record_command(timeout_seconds=2.0)

                # Transcribe
                input_text = stt.transcribe(command_audio)

                # Clear buffer
                recorder.clear_buffer()
                wake_word.reset()

                if input_text:
                    print(f"[AUDIO] Transcription: {input_text}")

                    # Process command - returns True if system command handled
                    is_system_command = process_command(input_text, state_manager, speaker, args)

                    if not is_system_command:
                        # Not a system command - run emotion LLM and respond
                        emotion = emotion_llm.classify(input_text)
                        print(f"[AUDIO] Emotion: {emotion}")
                        speaker.speak(emotion)
                    # else: system command already handled, no emotion response needed

                else:
                    print("[AUDIO] No speech detected")

                print("[AUDIO] Listening for wake word again...\n")

    finally:
        recorder.stop_listening()
        print("[AUDIO] Stopped")

# ============================================================================
# MAIN
# ============================================================================

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="R2-D2 Complete System")
    parser.add_argument('--cpu', action='store_true', help='Use CPU YOLO instead of Hailo for tracking')
    parser.add_argument('--local', action='store_true', help='Use local GPU (Ollama) instead of Groq API for audio')
    parser.add_argument('--debug-tracking', action='store_true', help='Enable debug output for tracking subsystem')
    parser.add_argument('--debug-heyr2', action='store_true', help='Enable debug output for HeyR2 audio subsystem')
    args = parser.parse_args()

    # Initialize state manager
    state_manager = StateManager()

    print("=" * 60)
    print("R2-D2 SYSTEM STARTING")
    print("=" * 60)
    print("Both tracking and audio systems are ACTIVE by default")
    print("Press Ctrl+C to shutdown")
    print("=" * 60)

    # Create threads for each subsystem
    tracker_thread = threading.Thread(
        target=tracking_loop,
        args=(state_manager, args),
        name="TrackerThread",
        daemon=True
    )

    audio_thread = threading.Thread(
        target=audio_loop,
        args=(state_manager, args),
        name="AudioThread",
        daemon=True
    )

    # Start both subsystems
    tracker_thread.start()
    audio_thread.start()

    # Main thread waits for shutdown
    try:
        while not state_manager.should_shutdown():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("SHUTDOWN REQUESTED")
        print("=" * 60)
        state_manager.request_shutdown()

    # Wait for threads to finish cleanup
    tracker_thread.join(timeout=5.0)
    audio_thread.join(timeout=5.0)

    print("=" * 60)
    print("R2-D2 SYSTEM STOPPED")
    print("=" * 60)

if __name__ == "__main__":
    main()
