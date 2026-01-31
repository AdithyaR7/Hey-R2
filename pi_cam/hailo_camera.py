#!/usr/bin/env python3
"""
Person detection using Hailo AI HAT+ with Picamera2.
Tracks person position and calculates horizontal offset from screen center.
"""

import os
import time
import cv2
from picamera2 import Picamera2
from picamera2.devices import Hailo

# COCO class names (person is class 0)
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush"
]

class HailoCamera:
    def __init__(self, model_path="/usr/share/hailo-models/weights/yolov6n_h8l.hef",
                 flip=True, threshold=0.6, debug=False):
        """
        Initialize Hailo-accelerated camera.
        """
        self.flip = flip
        self.threshold = threshold
        self.debug = debug
        self.headless = os.environ.get('DISPLAY') is None

        print(f"Loading Hailo model: {model_path}")
        self.hailo = Hailo(model_path)
        self.model_h, self.model_w, _ = self.hailo.get_input_shape()
        self.class_names = COCO_CLASSES

        self.resolution = (self.model_w, self.model_h)
        self.screen_center_x = self.resolution[0] // 2
        self.screen_center_y = self.resolution[1] // 2

        print("Starting camera...")
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (self.model_w, self.model_h)},
            controls={'FrameRate': 60},
            buffer_count=2
        )
        self.picam2.configure(config)
        self.picam2.start()

        print(f"Camera started. {'Headless mode' if self.headless else 'Display enabled'}")
        print(f"Model input size: {self.model_w}x{self.model_h}")

        self.fps = 0.0
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.last_fps_print = time.time()

    def _extract_detections(self, hailo_output, w, h):
        results = []
        for class_id, detections in enumerate(hailo_output):
            for detection in detections:
                score = detection[4]
                if score >= self.threshold:
                    y0, x0, y1, x1 = detection[:4]
                    bbox = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
                    results.append({
                        'class_id': class_id,
                        'class_name': self.class_names[class_id],
                        'bbox': bbox,
                        'score': score
                    })
        return results

    def get_person_offset(self):
        self.frame_count += 1
        elapsed = time.time() - self.fps_start_time
        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.fps_start_time = time.time()

        frame = self.picam2.capture_array("main")

        if self.flip:
            frame = cv2.rotate(frame, cv2.ROTATE_180)

        results = self.hailo.run(frame)
        detections = self._extract_detections(results, self.resolution[0], self.resolution[1])

        offset_x = None
        confidence = None

        for det in detections:
            if det['class_id'] == 0:
                x1, y1, x2, y2 = det['bbox']
                confidence = det['score']

                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                offset_x = cx - self.screen_center_x
                if self.flip:
                    offset_x = -offset_x

                if not self.headless:
                    self._draw_visualization(frame, x1, y1, x2, y2, cx, cy, offset_x, confidence)

                direction = "RIGHT" if offset_x > 0 else "LEFT"

                if self.debug:
                    print(
                        f"FPS: {self.fps:5.1f} | "
                        f"Person at X={cx} | "
                        f"Offset: {offset_x:+4d}px ({direction:5s}) | "
                        f"Conf: {confidence:.2f}"
                    )

                break

        if not self.headless:
            cv2.imshow('Hailo Person Detection', frame)

        return offset_x, confidence

    def _draw_visualization(self, frame, x1, y1, x2, y2, cx, cy, offset_x, confidence):
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

        cv2.line(frame, (self.screen_center_x, 0),
                 (self.screen_center_x, self.resolution[1]), (255, 0, 0), 1)

        cv2.line(frame, (self.screen_center_x, cy), (cx, cy), (255, 255, 0), 2)

        direction = "RIGHT" if offset_x > 0 else "LEFT"
        cv2.putText(frame, f"{direction} {abs(offset_x)}px",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Conf: {confidence:.2f}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"FPS: {self.fps:.1f}",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    def check_quit(self):
        if not self.headless:
            return cv2.waitKey(1) & 0xFF == ord('q')
        return False

    def cleanup(self):
        self.picam2.stop()
        self.hailo.close()
        if not self.headless:
            cv2.destroyAllWindows()
        if self.debug:
            print("Camera cleaned up")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Hailo Person Detection')
    parser.add_argument('--model', default='/usr/share/hailo-models/yolov6n_h8l.hef')
    parser.add_argument('--threshold', type=float, default=0.6)
    parser.add_argument('--no-flip', action='store_true')
    parser.add_argument('--debug', action='store_true',
                        help='Print per-frame detection info')
    args = parser.parse_args()

    camera = HailoCamera(
        model_path=args.model,
        flip=not args.no_flip,
        threshold=args.threshold,
        debug=args.debug
    )

    try:
        print("Running detection... Press 'q' to quit (if display available) or Ctrl+C")
        while True:
            camera.get_person_offset()
            if camera.check_quit():
                break
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        camera.cleanup()


if __name__ == "__main__":
    main()
