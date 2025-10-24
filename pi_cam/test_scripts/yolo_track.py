#!/usr/bin/env python3
import cv2
import time
import os
from picamera2 import Picamera2
from ultralytics import YOLO

# Load model
print("Loading model...")
model = YOLO('yolov8n.pt')

# Check if display available
HEADLESS = os.environ.get('DISPLAY') is None

# FPS variables
fps_counter = 0
fps_timer = time.time()

# Screen center (for 640x480)
SCREEN_CENTER_X = 320

with Picamera2() as picam2:
    config = picam2.create_preview_configuration(
        main={"format": "RGB888", "size": (640, 480)},
        controls={"FrameRate": 30}
    )
    picam2.configure(config)
    picam2.start()
    print(f"Camera started. {'Headless mode' if HEADLESS else 'Press q to quit'}, Ctrl+C to exit")
    
    try:
        while True:
            frame = picam2.capture_array()
            
            # Run YOLO detection
            results = model(frame, imgsz=320, verbose=False)
            
            # Get person detections (class 0 in YOLO)
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        if int(box.cls) == 0:  # Person class
                            # Get first person only
                            x1, y1, x2, y2 = box.xyxy[0].int().tolist()
                            confidence = float(box.conf)
                            
                            # Calculate person center
                            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                            
                            # Calculate horizontal offset from screen center
                            offset_x = cx - SCREEN_CENTER_X
                            direction = "RIGHT" if offset_x > 0 else "LEFT"
                            
                            if not HEADLESS:
                                # Draw box and person center
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                                
                                # Draw screen center line (vertical)
                                cv2.line(frame, (SCREEN_CENTER_X, 0), (SCREEN_CENTER_X, 480), (255, 0, 0), 1)
                                
                                # Draw horizontal offset line
                                cv2.line(frame, (SCREEN_CENTER_X, cy), (cx, cy), (255, 255, 0), 2)
                                
                                # Display offset info
                                cv2.putText(frame, f"{direction} {abs(offset_x)}px", 
                                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                                           0.7, (255, 255, 255), 2)
                            
                            print(f"Person at X={cx} | Offset: {offset_x:+4d}px ({direction:5s})")
                            break  # Only track first person
                    break  # Only process first result
            
            # Display if available
            if not HEADLESS:
                cv2.imshow('Person Detection', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # FPS calculation
            fps_counter += 1
            if time.time() - fps_timer >= 2.0:
                fps = fps_counter / 2.0
                print(f"FPS: {fps:.1f}")
                fps_counter = 0
                fps_timer = time.time()
                
    except KeyboardInterrupt:
        print("\nInterrupted")

if not HEADLESS:
    cv2.destroyAllWindows()
print("Cleaned up")