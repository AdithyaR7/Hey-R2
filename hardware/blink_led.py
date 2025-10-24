import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
LED_PIN = 27  # Change to your GPIO pin

GPIO.setup(LED_PIN, GPIO.OUT)

def blink(interval=2):
    while True:
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(interval)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(interval)

try:
    print("blinking led")
    blink(2)
except KeyboardInterrupt:
    print("failed")
    GPIO.cleanup()