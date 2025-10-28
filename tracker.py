#!/usr/bin/env python3
import sys
import time
sys.path.append('pi_cam')
sys.path.append('hardware')

from camera import Camera
from motor import Motor

def main():
    # Initialize components
    print("Initializing R2 tracker...")
    camera = Camera(model_name='yolov8n.pt', resolution=(640, 480), fps=30, flip=True)
    motor = Motor(servo_pin=17)
    
    motor.move_home()
    print("Motor initialized to home - 90 degrees")
    time.sleep(2)
    
    offset_history = []
    SMOOTH_N = 3  # average over last 3 frames
    
    # Tracking stats
    fps_counter = 0
    fps_timer = time.time()
    tracking_active = False
    last_move_time = 0
    
    print("Tracking started. Press Ctrl+C to exit")
    if not camera.headless:
        print("Press 'q' to quit")
    
    try:
        while True:
            # Get person position
            offset, confidence = camera.get_person_offset()
            
            # Smooth the offset BEFORE using it
            if offset is not None:
                offset_history.append(offset)
                if len(offset_history) > SMOOTH_N:
                    offset_history.pop(0)
                smoothed_offset = int(sum(offset_history) / len(offset_history))
                
                if not tracking_active:
                    print(f"Target acquired! Confidence: {confidence:.2f}")
                    tracking_active = True
                
                # Rate limit motor updates
                current_time = time.time()
                if current_time - last_move_time > 0.1:  # 10Hz max
                    moved = motor.move_by_offset(smoothed_offset)  # Use ONE method only
                    last_move_time = current_time
                    
                    if not moved:
                        print("Centered - in dead zone")
            else:
                offset_history = []  # Clear history on target loss
                if tracking_active:
                    print("Target lost")
                    motor.stop()
                    tracking_active = False
            
            # Check for quit
            if camera.check_quit():
                break
            
            # FPS calculation
            fps_counter += 1
            if time.time() - fps_timer >= 3.0:
                fps = fps_counter / 3.0
                print(f"[Tracking FPS: {fps:.1f}]")
                fps_counter = 0
                fps_timer = time.time()
                
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        time.sleep(1)
        print("Returning home...")
        motor.move_home()
        print("Cleaning up...")
        camera.cleanup()
        motor.cleanup()
        print("R2 tracker stopped")

if __name__ == "__main__":
    main()