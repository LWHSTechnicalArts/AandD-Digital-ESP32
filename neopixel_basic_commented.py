# Save on the CIRCUITPY drive as code.py

# --- Libraries ----------------------------------------------------------
# "import" brings in code someone else already wrote so we can use it.
import time       # lets us pause the program with time.sleep()
import board      # names for the physical pins on this board
import neopixel   # knows how to talk to NeoPixel LED strips

# --- Settings -----------------------------------------------------------
# These are in CAPS to signal "these are the knobs you can turn."
# Change these numbers and re-save to see what happens.
PIXEL_PIN = board.D5   # the pin wired to the strip's DIN
NUM_PIXELS = 16        # how many LEDs on your strip
BRIGHTNESS = 0.5       # 0.0 to 1.0 - keep it low, bright LEDs use a lot of power
DELAY = 1              # seconds each color stays on

# Build the strip object. From here on, "pixels" IS the strip -
# anything we want the LEDs to do, we ask "pixels" to do.
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=BRIGHTNESS)

# --- Colors -------------------------------------------------------------
# Every color is three numbers: (red, green, blue).
# Each one runs 0 (off) to 255 (full). Mixing them makes every other color -
# YELLOW below is just red and green together, with no blue.
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)

# --- Main loop ----------------------------------------------------------
# "while True" means repeat forever, until the board is unplugged or reset.
while True:

    # Step through the list one color at a time. Each time around,
    # the variable "color" holds the next color in the list.
    for color in [RED, GREEN, BLUE]:
        print("Showing:", color)   # sends text to the serial console
        pixels.fill(color)         # sets every LED on the strip to this color
        time.sleep(DELAY)          # wait here before moving on

    # Once the loop finishes all three, flash yellow before starting over.
    print("Showing:", YELLOW)
    pixels.fill(YELLOW)
    time.sleep(DELAY)
