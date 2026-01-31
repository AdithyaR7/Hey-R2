#!/usr/bin/env python3
import time
import os
import threading
import math
from rpi_hardware_pwm import HardwarePWM

CAM_FOV = 77    # degrees
IMG_WIDTH = 640 # pixels

class Motor:
    def __init__(self, servo_pin=12, position_file='motor_position.txt'):
        """Initialize threaded motor control"""
        self.servo_pin = servo_pin
        self.position_file = position_file

        # Initialize hardware PWM (GPIO 12 = PWM channel 0)
        # Standard servo: 50Hz, duty cycle 2.5% = 0°, 7.5% = 90°, 12.5% = 180°
        self.pwm = HardwarePWM(pwm_channel=0, hz=50)
        self.pwm.start(0)

        # Thread-safe variables
        self.lock = threading.Lock()
        self.target_angle = 90.0  # Target angle (updated by main thread)
        self.current_angle = 90.0  # Current angle (updated by motor thread)

        # Thread control
        self.running = False
        self.motor_thread = None

        # Control parameters
        self.pixels_per_degree = IMG_WIDTH / CAM_FOV  # 640px/77° ≈ 8.3 px/deg

        # EMA filter for input smoothing
        self.ema_alpha = 0.2  # 0-1, lower = smoother but more lag
        self.ema_offset = 0.0

        # Smoothing parameters (tuned)
        self.interpolation_speed = 0.7  # 0-1, higher = faster response to target changes
        self.MIN_MOVEMENT = 0.1  # degrees - minimum step size for smooth motion
        # self.MAX_SPEED = 200.0  # degrees/sec - maximum angular velocity
        # self.DEADBAND_PIXELS = 20  # pixels - ignore small offsets to prevent jitter
        # self.sigmoid_scale = 8.0  # Scaling factor for sigmoid curve
        self.MAX_SPEED = 150.0  # degrees/sec - maximum angular velocity
        self.DEADBAND_PIXELS = 15  # pixels - ignore small offsets to prevent jitter
        self.sigmoid_scale = 10.0  # Scaling factor for sigmoid curve (higher = smoother)

        print(f"Motor initialized at {self.current_angle}°")

    def clamp_angle(self, angle):
        """Clamp angle to valid range 0-180"""
        return max(0.0, min(180.0, angle))

    def angle_to_duty_cycle(self, angle):
        """Convert angle (0-180) to duty cycle percentage (2.5-12.5%)"""
        # 0° = 2.5%, 90° = 7.5%, 180° = 12.5%
        return 2.5 + (angle / 180.0) * 10.0

    def set_target_from_offset(self, pixel_offset):
        """
        Update target angle from pixel offset (called by main thread at ~60 FPS).
        Thread-safe, non-blocking.

        Args:
            pixel_offset: Signed pixel offset from center (-320 to +320)
        """
        # EMA filter - smooth noisy YOLO detections
        self.ema_offset = self.ema_alpha * pixel_offset + (1 - self.ema_alpha) * self.ema_offset
        pixel_offset = self.ema_offset

        # Deadband - ignore small offsets to prevent jitter from camera noise
        if abs(pixel_offset) < self.DEADBAND_PIXELS:
            return  # Don't update target, motor stays steady

        # Convert pixel error to angle error
        angle_error = pixel_offset / self.pixels_per_degree

        # Calculate desired target (proportional control)
        # Kp = 0.2  # Proportional gain (was 0.3)
        Kp = 0.15  # Proportional gain
        angle_change = angle_error * Kp

        # Update target angle (thread-safe)
        # Sigmoid interpolation in control loop handles smoothness
        with self.lock:
            self.target_angle = self.clamp_angle(self.current_angle + angle_change)
            print(f"Target update: offset={pixel_offset:+6.1f}px ({angle_error:+.1f}°) → target={self.target_angle:.1f}°")

    def _control_loop(self):
        """
        High-frequency motor control loop (runs in separate thread at ~100 Hz).
        Smoothly interpolates current angle towards target angle.
        """
        loop_rate = 100  # Hz
        dt = 1.0 / loop_rate

        # For rate monitoring
        loop_count = 0
        rate_timer = time.time()

        while self.running:
            loop_start = time.time()

            with self.lock:
                # Calculate error
                error = self.target_angle - self.current_angle

                # Sigmoid S-curve for smooth acceleration/deceleration
                # tanh creates smooth transitions: slow start → fast middle → slow end
                normalized_error = error / self.sigmoid_scale
                smooth_factor = math.tanh(normalized_error)  # Returns -1 to 1, smooth S-curve

                # Calculate step based on smooth factor
                step = smooth_factor * self.MAX_SPEED * dt

                # Only update if movement is significant
                if abs(step) > self.MIN_MOVEMENT * dt:
                    self.current_angle += step
                    self.current_angle = self.clamp_angle(self.current_angle)

                    # Send PWM command
                    duty = self.angle_to_duty_cycle(self.current_angle)
                    self.pwm.change_duty_cycle(duty)

            # Maintain loop rate
            elapsed = time.time() - loop_start
            sleep_time = dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

            # Print actual loop rate every 3 seconds
            loop_count += 1
            if time.time() - rate_timer >= 1.0:
                actual_rate = loop_count / 1.0
                print(f"[Motor loop: {actual_rate:.1f} Hz]")
                loop_count = 0
                rate_timer = time.time()

    def start_control_loop(self):
        """Start the motor control thread"""
        if self.running:
            print("Motor control loop already running")
            return

        self.running = True
        self.motor_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.motor_thread.start()
        print("Motor control loop started (100 Hz)")

    def stop_control_loop(self):
        """Stop the motor control thread"""
        if not self.running:
            return

        self.running = False
        if self.motor_thread:
            self.motor_thread.join(timeout=1.0)
        print("Motor control loop stopped")

    def move_slow(self, target_angle, step=1):
        """Move motor slowly from current position to target angle (blocking)"""
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

        with self.lock:
            self.current_angle = float(target_angle)
            self.target_angle = float(target_angle)

    def move_home(self):
        """Move to home position (90°)"""
        self.move_slow(target_angle=90, step=1)
        time.sleep(1)

    def stop(self):
        """Stop PWM signal completely"""
        try:
            self.pwm.change_duty_cycle(0)  # Turn off PWM
        except:
            pass

    def cleanup(self):
        """Clean up hardware PWM and stop thread"""
        self.stop_control_loop()
        self.pwm.stop()
        print(f"Motor cleaned up at position {self.current_angle:.1f}°")