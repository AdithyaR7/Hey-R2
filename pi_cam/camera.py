#!/usr/bin/env python3
import cv2
import os
from picamera2 import Picamera2
from ultralytics import YOLO

class Camera:
    def __init__(self, model_name='yolov8n.pt', resolution=(640, 480), fps=30, flip=True):
        """Initialize camera and YOLO model"""
        print("Loading model...")
        self.model = YOLO(model_name)
        
        # Screen center
        self.screen_center_x = resolution[0] // 2
        self.screen_center_y = resolution[1] // 2
        
        # Check if display available - < export DISPLAY=:0 > for display with ssh
        self.headless = os.environ.get('DISPLAY') is None
        self.flip = flip      # flip camera feed 180 based on mount orientation
        
        # Setup camera
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={"format": "RGB888", "size": resolution},
            controls={"FrameRate": fps}
        )
        self.picam2.configure(config)
        self.picam2.start()
        print(f"Camera started. {'Headless mode' if self.headless else 'Display enabled'}")
        
        self.resolution = resolution
        
    def get_person_offset(self):
        """
        Capture frame and detect person.
        Returns: (offset_x, confidence) or (None, None) if no person detected
        """
        frame = self.picam2.capture_array()
        if self.flip:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        
        # Run YOLO detection
        results = self.model(frame, imgsz=320, verbose=False)
        
        offset_x = None
        confidence = None
        
        # Get person detections (class 0 in YOLO)
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    if int(box.cls) == 0 and float(box.conf) > 0.6:  # Person class
                        # Get first person only
                        x1, y1, x2, y2 = box.xyxy[0].int().tolist()
                        confidence = float(box.conf)
                        
                        # Calculate person center
                        cx = (x1 + x2) // 2
                        cy = (y1 + y2) // 2
                        
                        # Calculate horizontal offset from screen center
                        offset_x = cx - self.screen_center_x
                        if self.flip: 
                            offset_x = -offset_x
                        
                        if not self.headless:
                            self._draw_visualization(frame, x1, y1, x2, y2, cx, cy, offset_x, confidence)
                        
                        # Print to terminal
                        direction = "RIGHT" if offset_x > 0 else "LEFT"
                        print(f"Person at X={cx} | Offset: {offset_x:+4d}px ({direction:5s}) | Conf: {confidence:.2f}")
                        
                        break  # Only track first person
                break  # Only process first result
        
        # Show frame if display available
        if not self.headless:
            cv2.imshow('Person Detection', frame)
            
        return offset_x, confidence
    
    def _draw_visualization(self, frame, x1, y1, x2, y2, cx, cy, offset_x, confidence):
        """Draw bounding box and tracking visualization"""
        # Draw box and person center
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
        
        # Draw screen center line (vertical)
        cv2.line(frame, (self.screen_center_x, 0), 
                (self.screen_center_x, self.resolution[1]), (255, 0, 0), 1)
        
        # Draw horizontal offset line
        cv2.line(frame, (self.screen_center_x, cy), (cx, cy), (255, 255, 0), 2)
        
        # Display offset info
        direction = "RIGHT" if offset_x > 0 else "LEFT"
        cv2.putText(frame, f"{direction} {abs(offset_x)}px", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Conf: {confidence:.2f}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.7, (255, 255, 255), 2)
    
    def check_quit(self):
        """Check if 'q' key pressed (only works with display)"""
        if not self.headless:
            return cv2.waitKey(1) & 0xFF == ord('q')
        return False
    
    def cleanup(self):
        """Clean up camera and display"""
        self.picam2.stop()
        if not self.headless:
            cv2.destroyAllWindows()
        print("Camera cleaned up")