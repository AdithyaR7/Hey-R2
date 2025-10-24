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
    camera = Camera(model_name='yolov8n.pt', resolution=(640, 480), fps=30)
    motor = Motor(servo_pin=17)
    
    # Tracking stats
    fps_counter = 0
    fps_timer = time.time()
    tracking_active = False
    
    print("Tracking started. Press Ctrl+C to exit")
    if not camera.headless:
        print("Press 'q' to quit")
    
    try:
        while True:
            # Get person position
            offset, confidence = camera.get_person_offset()
            
            # Move motor if person detected
            if offset is not None:
                if not tracking_active:
                    print(f"Target acquired! Confidence: {confidence:.2f}")
                    tracking_active = True
                
                # Use simple proportional method (or switch to move_by_offset_smooth)
                moved = motor.move_by_offset(offset)
                
                if not moved:
                    print("Centered - in dead zone")
            else:
                if tracking_active:
                    print("Target lost")
                    tracking_active = False
            
            # Check for quit
            if camera.check_quit():
                break
            
            # FPS calculation
            fps_counter += 1
            if time.time() - fps_timer >= 2.0:
                fps = fps_counter / 2.0
                print(f"[Tracking FPS: {fps:.1f}]")
                fps_counter = 0
                fps_timer = time.time()
                
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        print("Cleaning up...")
        camera.cleanup()
        motor.cleanup()
        print("R2 tracker stopped")

if __name__ == "__main__":
    main()