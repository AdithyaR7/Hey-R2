#!/usr/bin/env python3
import sys
import time
import argparse
sys.path.append('pi_cam')
sys.path.append('hardware')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cpu', action='store_true', help='Use CPU YOLO instead of Hailo')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    if args.cpu:
        from cpu_camera import Camera
        from motor import Motor
        camera = Camera(model_name='pi_cam/weights/yolo26n.pt', resolution=(640, 480), fps=30, flip=True)
        motor = Motor(servo_pin=12, debug=args.debug)
        use_threaded = False
    else:
        from hailo_camera import HailoCamera
        from motor_threaded import Motor
        camera = HailoCamera(model_path='pi_cam/weights/yolov6n_h8l.hef', flip=True)
        motor = Motor(servo_pin=12, debug=args.debug)
        use_threaded = True

    print(f"Mode: {'CPU' if args.cpu else 'Hailo'}")
    print(f"Motor: {'Threaded' if use_threaded else 'Direct PID'}")

    motor.move_home()
    if args.debug:
        print("Motor initialized to home - 90 degrees")
    time.sleep(2)

    if use_threaded:
        motor.start_control_loop()

    fps_counter = 0
    fps_timer = time.time()
    tracking_active = False

    print("Tracking started. Press Ctrl+C to exit")
    if not camera.headless:
        print("Press 'q' to quit")

    try:
        while True:
            offset, confidence = camera.get_person_offset()

            if offset is not None:
                if not tracking_active:
                    if args.debug:
                        print(f"Target acquired! Confidence: {confidence:.2f}")
                    tracking_active = True

                if use_threaded:
                    motor.set_target_from_offset(offset)
                else:
                    moved = motor.move_by_offset_pid(offset)
                    if not moved and args.debug:
                        print("Centered - minimal movement")
            else:
                if use_threaded:
                    if tracking_active and args.debug:
                        print("Target lost")
                    tracking_active = False
                else:
                    motor.pid.reset()
                    if tracking_active:
                        if args.debug:
                            print("Target lost")
                        motor.stop()
                        tracking_active = False

            if camera.check_quit():
                break

            fps_counter += 1
            if time.time() - fps_timer >= 3.0:
                fps = fps_counter / 3.0
                if args.debug:
                    if use_threaded:
                        print(f"[Detection FPS: {fps:.1f}] [Motor running at 100 Hz]")
                    else:
                        print(f"[Tracking FPS: {fps:.1f}]")
                fps_counter = 0
                fps_timer = time.time()

    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if use_threaded:
            if args.debug:
                print("Stopping motor control loop...")
            motor.stop_control_loop()
            time.sleep(0.5)
        else:
            time.sleep(1)

        if args.debug:
            print("Returning home...")
        motor.move_home()
        if args.debug:
            print("Cleaning up...")
        camera.cleanup()
        motor.cleanup()
        print("R2 tracker stopped")

if __name__ == "__main__":
    main()
