#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import os

class Motor:
    def __init__(self, servo_pin=17, position_file='motor_position.txt'):
        """Initialize motor control"""
        self.servo_pin = servo_pin
        self.position_file = position_file
        
        # GPIO setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.servo_pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.servo_pin, 50)
        self.pwm.start(0)
        
        # Read initial position
        self.current_angle = self.read_position()
        print(f"Motor initialized at {self.current_angle}°")
        
        # Control parameters
        self.pixels_per_degree = 3.5  # 640px/180° ≈ 3.5 (tune this!)
        self.dead_zone = 20  # Ignore small offsets
        self.max_speed = 5  # Max degrees per update
        
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
        return max(0, min(180, angle))
    
    def set_angle(self, angle):
        """Move motor instantly to angle"""
        angle = self.clamp_angle(angle)
        duty = 2.5 + (angle / 18)
        self.pwm.ChangeDutyCycle(duty)
        time.sleep(0.5)
        self.current_angle = angle
        self.write_position(angle)
    
    def move_slow(self, target_angle, step=1):
        """Move motor slowly from current position to target angle"""
        target_angle = self.clamp_angle(target_angle)
        start = self.current_angle
        
        if target_angle > start:
            angles = range(start, target_angle + 1, step)
        else:
            angles = range(start, target_angle - 1, -step)
        
        for angle in angles:
            duty = 2.5 + (angle / 18)
            self.pwm.ChangeDutyCycle(duty)
            time.sleep(0.02)
        
        self.current_angle = target_angle
        self.write_position(target_angle)
    
    def move_by_offset(self, pixel_offset):
        """
        Convert pixel offset to motor movement.
        Uses proportional control - larger offset = larger movement.
        
        Args:
            pixel_offset: Signed pixel offset from center (-320 to +320)
        
        Returns:
            bool: True if moved, False if in dead zone
        """
        # Check dead zone
        if abs(pixel_offset) < self.dead_zone:
            return False
        
        # Proportional control: larger offset = larger movement
        # But cap at max_speed for smooth movement
        angle_change = pixel_offset / self.pixels_per_degree
        angle_change = max(-self.max_speed, min(self.max_speed, angle_change))
        
        # Calculate target
        target_angle = self.clamp_angle(self.current_angle + angle_change)
        
        # Single-step movement (non-blocking)
        duty = 2.5 + (target_angle / 18)
        self.pwm.ChangeDutyCycle(duty)
        
        self.current_angle = target_angle
        self.write_position(target_angle)
        
        return True
    
    def move_by_offset_smooth(self, pixel_offset):
        """
        Alternative: Smoother P-controller with velocity.
        Movement speed proportional to offset distance.
        """
        if abs(pixel_offset) < self.dead_zone:
            return False
        
        # P-control: speed proportional to error
        Kp = 0.02  # Proportional gain (tune this!)
        angle_change = Kp * pixel_offset
        
        # Limit maximum change per update
        angle_change = max(-self.max_speed, min(self.max_speed, angle_change))
        
        target_angle = self.clamp_angle(self.current_angle + angle_change)
        
        # Move immediately
        duty = 2.5 + (target_angle / 18)
        self.pwm.ChangeDutyCycle(duty)
        
        self.current_angle = target_angle
        self.write_position(target_angle)
        
        return True
    
    def cleanup(self):
        """Clean up GPIO"""
        self.pwm.stop()
        GPIO.cleanup()
        print(f"Motor cleaned up at position {self.current_angle}°")