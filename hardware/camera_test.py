from picamera2 import Picamera2
import cv2

FPS = 20

with Picamera2() as picam2:
    config = picam2.create_preview_configuration(
        main={"format": "BGR888"},
        controls={"FrameRate": FPS}
    )
    picam2.configure(config)
    picam2.start()
    print(f"Starting camera at {FPS} fps.")

    while True:
        frame = picam2.capture_array()
        cv2.imshow('Camera', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

print("done ")
cv2.destroyAllWindows()