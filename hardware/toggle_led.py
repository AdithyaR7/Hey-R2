import lgpio

# Setup
LED_PIN = 17
led_state = False

h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, LED_PIN)

print("Press ENTER to toggle LED, Ctrl+C to quit")

try:
    while True:
        input()
        led_state = not led_state
        lgpio.gpio_write(h, LED_PIN, 1 if led_state else 0)
        print(f"LED: {'ON' if led_state else 'OFF'}")

except KeyboardInterrupt:
    print("\nExiting...")

finally:
    lgpio.gpiochip_close(h)