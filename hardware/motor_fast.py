#!/usr/bin/env python3
import time
from rpi_hardware_pwm import HardwarePWM

CAM_FOV = 77    # degrees
IMG_WIDTH = 640 # pixels

class Motor:
    def __init__(self, servo_pin=12):
        """Initialize simple PID motor control"""
        self.servo_pin = servo_pin

        # Initialize hardware PWM (GPIO 12 = PWM channel 0)
        # Standard servo: 50Hz, duty cycle 2.5% = 0°, 7.5% = 90°, 12.5% = 180°
        self.pwm = HardwarePWM(pwm_channel=0, hz=50)
        self.pwm.start(0)

        self.current_angle = 90.0
        self.pixels_per_degree = IMG_WIDTH / CAM_FOV  # ~8.3 px/deg

        # PID parameters (tune these)
        # self.Kp = 0.08
        # self.Kd = 0.04
        self.Kp = 0.06
        self.Kd = 0.008
        self.previous_error = 0.0

        # EMA filter for smoothing noisy detections
        self.ema_alpha = 0.25  # 0-1, lower = smoother but more lag
        self.ema_offset = 0.0

        # Control limits
        # self.DEADBAND_PIXELS = 20
        # self.MAX_ANGLE_CHANGE = 2.0  # Max degrees per update
        self.DEADBAND_PIXELS = 10
        self.MAX_ANGLE_CHANGE = 1.0  # Max degrees per update

        # PID wrapper for compatibility
        self.pid = self

        print(f"Motor initialized at {self.current_angle}°")

    def clamp_angle(self, angle):
        """Clamp angle to valid range 0-180"""
        return max(0.0, min(180.0, angle))

    def angle_to_duty_cycle(self, angle):
        """Convert angle (0-180) to duty cycle percentage (2.5-12.5%)"""
        return 2.5 + (angle / 180.0) * 10.0

    # def move_by_offset_pid(self, pixel_offset):
    #     """
    #     Update motor position using squared proportional control.
    #     Called at 50 FPS from tracker loop.
        
    #     Args:
    #         pixel_offset: Signed pixel offset from center (-320 to +320)
            
    #     Returns:
    #         bool: True if motor moved, False if in deadband
    #     """
    #     # Deadband - ignore small offsets
    #     if abs(pixel_offset) < self.DEADBAND_PIXELS:
    #         return False
        
    #     # Squared proportional control (their approach)
    #     max_offset = IMG_WIDTH / 2  # 320 pixels
    #     normalized_error = (abs(pixel_offset) / max_offset) ** 2  # 0 to 1, squared
        
    #     # Maximum angle change per frame
    #     max_angle_per_frame = 30.0  # degrees (tune this)
        
    #     # Calculate angle change (preserve sign)
    #     angle_change = max_angle_per_frame * normalized_error
    #     if pixel_offset < 0:
    #         angle_change = -angle_change
        
    #     # Update angle
    #     self.current_angle = self.clamp_angle(self.current_angle + angle_change)
        
    #     # Set servo position
    #     duty = self.angle_to_duty_cycle(self.current_angle)
    #     self.pwm.change_duty_cycle(duty)
        
    #     print(f"Offset={pixel_offset:+4d}px | Change={angle_change:+.2f}° | Angle={self.current_angle:.1f}°")
        
    #     return True

    def move_by_offset_pid(self, pixel_offset):
        """
        Update motor position using PID control.
        Called at 60 FPS from tracker loop.
        
        Args:
            pixel_offset: Signed pixel offset from center (-320 to +320)
            
        Returns:
            bool: True if motor moved, False if in deadband
        """
        # EMA filter - smooth noisy detections
        self.ema_offset = self.ema_alpha * pixel_offset + (1 - self.ema_alpha) * self.ema_offset
        pixel_offset = self.ema_offset

        # Deadband - ignore small offsets
        if abs(pixel_offset) < self.DEADBAND_PIXELS:
            self.previous_error = 0.0  # Reset derivative term
            return False

        # Convert pixel error to angle error
        error = pixel_offset / self.pixels_per_degree
        
        # PID calculation
        P = self.Kp * error
        D = self.Kd * (error - self.previous_error)
        
        angle_change = P + D
        
        # Limit maximum change per update
        angle_change = max(-self.MAX_ANGLE_CHANGE, 
                          min(self.MAX_ANGLE_CHANGE, angle_change))
        
        # Update angle
        self.current_angle = self.clamp_angle(self.current_angle + angle_change)
        
        # Set servo position
        duty = self.angle_to_duty_cycle(self.current_angle)
        self.pwm.change_duty_cycle(duty)
        
        # Store error for next derivative calculation
        self.previous_error = error
        
        print(f"Offset={pixel_offset:+6.1f}px | Error={error:+.1f}° | "
              f"P={P:+.2f} D={D:+.2f} | Angle={self.current_angle:.1f}°")
        
        return True

    def reset(self):
        """Reset PID state (called when target lost)"""
        self.previous_error = 0.0
        self.ema_offset = 0.0

    def move_slow(self, target_angle, step=1):
        """Move motor slowly to target angle (blocking)"""
        target_angle = int(self.clamp_angle(target_angle))
        start = int(self.current_angle)

        if target_angle > start:
            angles = range(start, target_angle + 1, step)
        else:
            angles = range(start, target_angle - 1, -step)

        for angle in angles:
            duty = self.angle_to_duty_cycle(angle)
            self.pwm.change_duty_cycle(duty)
            time.sleep(0.02)

        self.current_angle = float(target_angle)
        self.previous_error = 0.0

    def move_home(self):
        """Move to home position (90°)"""
        self.move_slow(target_angle=90, step=1)
        time.sleep(1)

    def stop(self):
        """Stop PWM signal completely"""
        try:
            self.pwm.change_duty_cycle(0)
        except:
            pass

    def cleanup(self):
        """Clean up hardware PWM"""
        self.pwm.stop()
        print(f"Motor cleaned up at position {self.current_angle:.1f}°")