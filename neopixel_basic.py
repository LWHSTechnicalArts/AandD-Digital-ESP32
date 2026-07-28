# Save on the CIRCUITPY drive as code.py

import time
import board
import neopixel

PIXEL_PIN = board.D5   # the pin wired to the strip's DIN
NUM_PIXELS = 16        # how many LEDs on your strip
BRIGHTNESS = 0.5       # 0.0 to 1.0 - keep it low, bright LEDs use a lot of power
DELAY = 1              # seconds each color stays on

pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=BRIGHTNESS)

RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)

while True:
    for color in [RED, GREEN, BLUE]:
        print("Showing:", color)
        pixels.fill(color)
        time.sleep(DELAY)

    pixels.fill(YELLOW)
    print("Showing:", color)
    time.sleep(DELAY)
