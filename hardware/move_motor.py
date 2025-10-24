import RPi.GPIO as GPIO
import time
import argparse
import os

GPIO.setmode(GPIO.BCM)
SERVO_PIN = 17
POSITION_FILE = 'motor_position.txt'

GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def clamp_angle(angle):
    """Clamp angle to valid range 0-180"""
    return max(0, min(180, angle))

def read_position():
    """Read current position from file"""
    if os.path.exists(POSITION_FILE):
        with open(POSITION_FILE, 'r') as f:
            return int(f.read().strip())
    return 90  # Default if file doesn't exist

def write_position(angle):
    """Write current position to file"""
    with open(POSITION_FILE, 'w') as f:
        f.write(str(int(angle)))

def set_angle(angle):
    """Move motor instantly to angle"""
    duty = 2.5 + (angle / 18)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    write_position(angle)

def move_slow(target_angle, step=1):
    """Move motor slowly from current position to target angle"""
    start = read_position()
    
    if target_angle > start:
        angles = range(start, target_angle + 1, step)
    else:
        angles = range(start, target_angle - 1, -step)
    
    for angle in angles:
        duty = 2.5 + (angle / 18)
        pwm.ChangeDutyCycle(duty)
        time.sleep(0.02)
    
    write_position(target_angle)

parser = argparse.ArgumentParser(description='Control servo motor angle')
parser.add_argument('-a', '--angle', type=float, default=90, help='Angle to move servo (0-180)')
parser.add_argument('-m', '--method', choices=['slow', 'fast'], default='slow', 
                    help='Movement method (default: slow)')
args = parser.parse_args()

angle = clamp_angle(args.angle)

if args.method == 'slow':
    move_slow(int(args.angle))
else:
    set_angle(args.angle)

print(f"Moved to {args.angle} degrees using {args.method} method")

pwm.stop()
GPIO.cleanup()