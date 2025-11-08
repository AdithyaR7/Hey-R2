import time
import argparse
import os
from rpi_hardware_pwm import HardwarePWM

SERVO_PIN = 12  # GPIO 12 = PWM0
POSITION_FILE = 'motor_position.txt'

# Initialize hardware PWM
# GPIO 12 = PWM channel 0, GPIO 13 = PWM channel 1
# Standard servo: 50Hz frequency
# Duty cycle: 2.5% = 0°, 7.5% = 90°, 12.5% = 180°
pwm = HardwarePWM(pwm_channel=0, hz=50)
pwm.start(0)  # Start with 0% duty cycle

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

def angle_to_duty_cycle(angle):
    """Convert angle (0-180) to duty cycle percentage (2.5-12.5%)"""
    # 0° = 2.5%, 90° = 7.5%, 180° = 12.5%
    # Formula: duty = 2.5 + (angle / 180) * 10
    return 2.5 + (angle / 180.0) * 10.0

def set_angle(angle):
    """Move motor instantly to angle"""
    duty = angle_to_duty_cycle(angle)
    pwm.change_duty_cycle(duty)
    time.sleep(0.5)
    pwm.change_duty_cycle(0)  # Stop PWM signal
    write_position(angle)

def move_slow(target_angle, step=1):
    """Move motor slowly from current position to target angle"""
    start = read_position()

    if target_angle > start:
        angles = range(start, target_angle + 1, step)
    else:
        angles = range(start, target_angle - 1, -step)

    for angle in angles:
        duty = angle_to_duty_cycle(angle)
        pwm.change_duty_cycle(duty)
        time.sleep(0.02)

    pwm.change_duty_cycle(0)  # Stop PWM after movement
    write_position(target_angle)

parser = argparse.ArgumentParser(description='Control servo motor angle')
parser.add_argument('-a', '--angle', type=float, default=90, help='Angle to move servo (0-180)')
parser.add_argument('-m', '--method', choices=['slow', 'fast'], default='fast',
                    help='Movement method (default: slow)')
args = parser.parse_args()

# Clamp angle to valid range
angle = clamp_angle(args.angle)

if args.method == 'slow':
    move_slow(int(angle))
else:
    set_angle(angle)

print(f"Moved to {args.angle} degrees using {args.method} method")

pwm.stop()  # Stop hardware PWM