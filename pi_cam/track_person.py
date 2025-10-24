#!/usr/bin/env python3
import cv2
import numpy as np
import time
from picamera2 import Picamera2

# Load model
print("Loading model...")
net = cv2.dnn.readNetFromCaffe('deploy.prototxt', 'MobileNetSSD_deploy.caffemodel')

# FPS variables
fps_counter = 0
fps_timer = time.time()

with Picamera2() as picam2:
    config = picam2.create_preview_configuration(
        main={"format": "RGB888", "size": (640, 480)},
        controls={"FrameRate": 30}
    )
    picam2.configure(config)
    picam2.start()
    print("Camera started. Press 'q' to quit or Ctrl+C")
    
    try:
        while True:
            frame = picam2.capture_array()
            
            # Prepare image for model
            blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
            net.setInput(blob)
            detections = net.forward()
            
            # Find persons (class 15)
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                class_id = int(detections[0, 0, i, 1])
                
                if class_id == 15 and confidence > 0.5:  # Person detected
                    # Get bounding box
                    box = detections[0, 0, i, 3:7] * np.array([640, 480, 640, 480])
                    x1, y1, x2, y2 = box.astype("int")
                    
                    # Calculate center
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    
                    # Draw box and center
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                    cv2.putText(frame, f"Person {confidence:.2f}", 
                               (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.5, (0, 255, 0), 2)
            
            cv2.imshow('Person Detection', frame)
            
            # FPS calculation
            fps_counter += 1
            if time.time() - fps_timer >= 2.0:
                fps = fps_counter / 2.0
                print(f"FPS: {fps:.1f}")
                fps_counter = 0
                fps_timer = time.time()
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nInterrupted")

cv2.destroyAllWindows()
print("Cleaned up")