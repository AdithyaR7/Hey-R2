import lgpio
import time
import threading

class LED:
    """Controls R2-D2's two LEDs: status (red) and flashlight"""

    STATUS_PIN = 17
    FLASHLIGHT_PIN = 27

    def __init__(self):
        self.h = lgpio.gpiochip_open(0)
        # Defaults the pins to LOW / off on init
        lgpio.gpio_claim_output(self.h, self.STATUS_PIN)
        lgpio.gpio_claim_output(self.h, self.FLASHLIGHT_PIN)

        self._status_on = False
        self._flashlight_on = False
        self._blink_stop_event = threading.Event()

    def set_status_light(self, on: bool):
        """Set the red status LED on or off"""
        self._status_on = on
        lgpio.gpio_write(self.h, self.STATUS_PIN, 1 if on else 0)

    def set_flashlight(self, on: bool):
        """Set the flashlight LED on or off"""
        self._flashlight_on = on
        lgpio.gpio_write(self.h, self.FLASHLIGHT_PIN, 1 if on else 0)

    def blink_status_light(self, hz: float = 2.0, seconds: float = 1.5):
        """Blink the status LED at a given frequency for a duration in seconds"""
        interval = 1.0 / hz / 2  # half period (on time = off time)
        count = int(hz * seconds)
        for _ in range(count):
            self.set_status_light(True)
            time.sleep(interval)
            self.set_status_light(False)
            time.sleep(interval)

    def blink_flashlight(self, hz: float = 2.0, seconds: float = 1.5):
        """Blink the flashlight LED at a given frequency for a duration in seconds"""
        interval = 1.0 / hz / 2
        count = int(hz * seconds)
        for _ in range(count):
            self.set_flashlight(True)
            time.sleep(interval)
            self.set_flashlight(False)
            time.sleep(interval)

    def blink_status_light_continuous(self, hz: float = 2.0):
        """Blink the status LED indefinitely until stop_blink_status_light_continuous() is called"""
        self._blink_stop_event.clear()
        interval = 1.0 / hz / 2
        while not self._blink_stop_event.is_set():
            self.set_status_light(True)
            if self._blink_stop_event.wait(interval):
                break
            self.set_status_light(False)
            if self._blink_stop_event.wait(interval):
                break
        self.set_status_light(False)

    def stop_blink_status_light_continuous(self):
        """Stop the indefinite blink loop"""
        self._blink_stop_event.set()

    def cleanup(self):
        """Turn off both LEDs and release GPIO"""
        lgpio.gpio_write(self.h, self.STATUS_PIN, 0)
        lgpio.gpio_write(self.h, self.FLASHLIGHT_PIN, 0)
        lgpio.gpiochip_close(self.h)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LED Handler Test")
    parser.add_argument('function', choices=[
        'status_on', 'status_off',
        'flashlight_on', 'flashlight_off',
        'blink_status', 'blink_flashlight'
    ], help='Function to test')
    parser.add_argument('--hz', type=float, default=2.0, help='Blink frequency (default: 2.0)')
    parser.add_argument('--seconds', type=float, default=2.0, help='Blink duration in seconds (default: 2.0)')
    args = parser.parse_args()

    led = LED()

    try:
        if args.function == 'status_on':
            led.set_status_light(True)
            print("Status light ON - press Ctrl+C to exit")
            while True:
                time.sleep(1)

        elif args.function == 'status_off':
            led.set_status_light(False)
            print("Status light OFF")

        elif args.function == 'flashlight_on':
            led.set_flashlight(True)
            print("Flashlight ON - press Ctrl+C to exit")
            while True:
                time.sleep(1)

        elif args.function == 'flashlight_off':
            led.set_flashlight(False)
            print("Flashlight OFF")

        elif args.function == 'blink_status':
            print(f"Blinking status light at {args.hz} Hz for {args.seconds}s")
            led.blink_status_light(hz=args.hz, seconds=args.seconds)
            print("Done")

        elif args.function == 'blink_flashlight':
            print(f"Blinking flashlight at {args.hz} Hz for {args.seconds}s")
            led.blink_flashlight(hz=args.hz, seconds=args.seconds)
            print("Done")

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        led.cleanup()
