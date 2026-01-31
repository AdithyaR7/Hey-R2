#!/usr/bin/env python3
import time
import os
from rpi_hardware_pwm import HardwarePWM

CAM_FOV = 77    # degrees
IMG_WIDTH = 640 # pixels

class PIDController:
    """Simple PID controller for smooth tracking"""
    def __init__(self, Kp=0.8, Ki=0.0, Kd=0.3, derivative_filter=0.8, integral_limit=50):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.derivative_filter = derivative_filter  # Low-pass filter (0-1, lower = more filtering)
        self.integral_limit = integral_limit  # Anti-windup limit

        self.prev_error = 0
        self.prev_derivative = 0
        self.integral = 0

    def update(self, error, dt=1.0):
        """
        Calculate PID output with derivative filtering
        Args:
            error: Current error (pixel offset)
            dt: Time delta (we'll use 1.0 since frame rate varies)
        Returns:
            Control output (angle change in degrees)
        """
        # Proportional term
        P = self.Kp * error

        # Integral term (accumulated error) with anti-windup
        self.integral += error * dt
        # Clamp integral to prevent windup
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
        I = self.Ki * self.integral

        # Derivative term with low-pass filter to reduce noise
        derivative = (error - self.prev_error) / dt
        filtered_derivative = (self.derivative_filter * derivative +
                              (1 - self.derivative_filter) * self.prev_derivative)
        D = self.Kd * filtered_derivative

        self.prev_error = error
        self.prev_derivative = filtered_derivative

        return P + I + D

    def reset(self):
        """Reset PID state"""
        self.prev_error = 0
        self.prev_derivative = 0
        self.integral = 0

class Motor:
    def __init__(self, servo_pin=12, position_file='motor_position.txt', debug=False):
        """Initialize motor control"""
        self.servo_pin = servo_pin
        self.position_file = position_file
        self.debug = debug

        # Initialize hardware PWM (GPIO 12 = PWM channel 0)
        # Standard servo: 50Hz, duty cycle 2.5% = 0°, 7.5% = 90°, 12.5% = 180°
        self.pwm = HardwarePWM(pwm_channel=0, hz=50)
        self.pwm.start(0)

        # Always start at home position (90°)
        self.current_angle = 90
        if self.debug:
            print(f"Motor initialized at {self.current_angle}°")

        # Control parameters
        self.pixels_per_degree = IMG_WIDTH/CAM_FOV  # 640px/77° - tune

        # PID control parameters (tunable)
        self.MAX_SPEED_PER_UPDATE = 5.0  # degrees - prevents large jumps
        self.MIN_MOVEMENT = 0.5  # degrees - prevents micro-adjustments

        self.pid = PIDController(Kp=0.2, Ki=0.0, Kd=0.0)  # P-controller - moderately slow but works
        
        
        
    def read_position(self):
        """Read current position from file"""
        if os.path.exists(self.position_file):
            with open(self.position_file, 'r') as f:
                return int(f.read().strip())
        return 90  # Default center position
    
    def write_position(self, angle):
        """Write current position to file"""
        with open(self.position_file, 'w') as f:
            f.write(str(int(angle)))
    
    def clamp_angle(self, angle):
        """Clamp angle to valid range 0-180"""
        return int(max(0, min(180, angle)))

    def angle_to_duty_cycle(self, angle):
        """Convert angle (0-180) to duty cycle percentage (2.5-12.5%)"""
        # 0° = 2.5%, 90° = 7.5%, 180° = 12.5%
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle):
        """Move motor instantly to angle"""
        angle = self.clamp_angle(angle)

        duty = self.angle_to_duty_cycle(angle)
        self.pwm.change_duty_cycle(duty)
        time.sleep(0.05)

        self.current_angle = angle
        self.write_position(angle)
    
    def move_slow(self, target_angle, step=1):
        """Move motor slowly from current position to target angle"""
        target_angle = int(self.clamp_angle(target_angle))
        start = self.current_angle

        if target_angle > start:
            angles = range(start, target_angle + 1, step)
        else:
            angles = range(start, target_angle - 1, -step)

        for angle in angles:
            duty = self.angle_to_duty_cycle(angle)
            self.pwm.change_duty_cycle(duty)
            time.sleep(0.02)

        self.current_angle = target_angle
        self.write_position(target_angle)

    def move_by_offset_pid(self, pixel_offset):
        """
        PID-based tracking for smooth movement.

        Args:
            pixel_offset: Signed pixel offset from center (-320 to +320)

        Returns:
            bool: True if moved, False if no movement needed
        """
        # Convert pixel error to angle error
        angle_error = pixel_offset / self.pixels_per_degree

        # Update PID controller
        angle_change = self.pid.update(error=angle_error)

        # Apply rate limiting (prevent large jumps)
        angle_change = max(-self.MAX_SPEED_PER_UPDATE,
                          min(self.MAX_SPEED_PER_UPDATE, angle_change))

        # Calculate target with hardware limits
        target_angle = self.clamp_angle(self.current_angle + angle_change)

        # Verify actual movement is significant
        if abs(target_angle - self.current_angle) < self.MIN_MOVEMENT:
            return False

        # Update servo position with hardware PWM
        duty = self.angle_to_duty_cycle(target_angle)
        self.pwm.change_duty_cycle(duty)

        # Update state
        self.current_angle = target_angle

        if self.debug:
            print(f"PID: offset={pixel_offset:+4d}px ({angle_error:+.1f}°) → Δ={angle_change:+.1f}° → target={target_angle:.0f}°")

        return True
    
    def move_home(self):
        self.move_slow(target_angle=90, step=1)
        time.sleep(1)
        # Hardware PWM keeps running (servo holds position)
        return
    
    def stop(self):
        """Stop PWM signal completely"""
        try:
            self.pwm.change_duty_cycle(0)  # Turn off PWM
        except:
            pass

    def cleanup(self):
        """Clean up hardware PWM"""
        self.pwm.stop()
        if self.debug:
            print(f"Motor cleaned up at position {self.current_angle}°")