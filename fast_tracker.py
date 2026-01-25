#!/usr/bin/env python3
import sys
import time
sys.path.append('pi_cam')
sys.path.append('hardware')

from camera import Camera
from motor_threaded import Motor

def main():
    # Initialize components
    print("Initializing R2 tracker (threaded version)...")
    camera = Camera(model_name='pi_cam/yolo26n.pt', resolution=(640, 480), fps=30, flip=True)
    motor = Motor(servo_pin=17)

    motor.move_home()
    print("Motor initialized to home - 90 degrees")
    time.sleep(2)

    # Start motor control loop (runs at 100 Hz in background)
    motor.start_control_loop()

    # Tracking stats
    fps_counter = 0
    fps_timer = time.time()
    tracking_active = False

    print("Tracking started. Press Ctrl+C to exit")
    if not camera.headless:
        print("Press 'q' to quit")

    try:
        while True:
            # Get person position (runs at ~10 FPS due to YOLO)
            offset, confidence = camera.get_person_offset()

            if offset is not None:
                if not tracking_active:
                    print(f"Target acquired! Confidence: {confidence:.2f}")
                    tracking_active = True

                # Update target angle (non-blocking, motor thread handles smooth motion)
                motor.set_target_from_offset(offset)

            else:
                if tracking_active:
                    print("Target lost")
                    tracking_active = False
                # Motor continues smooth motion towards last known target

            # Check for quit
            if camera.check_quit():
                break

            # FPS calculation
            fps_counter += 1
            if time.time() - fps_timer >= 3.0:
                fps = fps_counter / 3.0
                print(f"[Detection FPS: {fps:.1f}] [Motor running at 100 Hz in background]")
                fps_counter = 0
                fps_timer = time.time()

    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        print("Stopping motor control loop...")
        motor.stop_control_loop()
        time.sleep(0.5)
        print("Returning home...")
        motor.move_home()
        print("Cleaning up...")
        camera.cleanup()
        motor.cleanup()
        print("R2 tracker stopped")

if __name__ == "__main__":
    main()
