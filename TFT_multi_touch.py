# SPDX-License-Identifier: Unlicense
#
# AI-assisted: "Claude (Anthropic)", August 2026
# Human contribution: idea / circuit design / pin mapping / debugging / testing on hardware
# Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

# Touch to cycle through five screens on the 3.5" TFT FeatherWing V2
#   image -> text -> shapes -> "Press somewhere" -> coordinates -> image
# The coordinates screen holds for two presses, so the reading updates once
# before you loop back around.

import board
import displayio
import fourwire
import terminalio
import adafruit_hx8357
import adafruit_tsc2007
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.triangle import Triangle

# --- Set up the screen --------------------------------------------------
displayio.release_displays()
spi = board.SPI()
display_bus = fourwire.FourWire(spi, command=board.D10, chip_select=board.D9)
display = adafruit_hx8357.HX8357(display_bus, width=480, height=320)

# --- Set up the touchscreen ---------------------------------------------
# The touch layer is a separate chip from the display, and it talks over
# I2C instead of SPI. That's why it needs its own setup.
i2c = board.STEMMA_I2C()
tsc = adafruit_tsc2007.TSC2007(i2c, irq=None)

# --- Colors -------------------------------------------------------------
RED = 0xFF0000
GREEN = 0x00FF00
BLUE = 0x0000FF
YELLOW = 0xFFFF00
CYAN = 0x00FFFF
WHITE = 0xFFFFFF

# --- Screen 1: the image ------------------------------------------------
image_group = displayio.Group()
bitmap = displayio.OnDiskBitmap("/image.bmp")
image_group.append(displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader))

# --- Screen 2: the text -------------------------------------------------
text_group = displayio.Group()
text_group.append(label.Label(terminalio.FONT, text="Hello World", color=RED, scale=2, x=20, y=50))
text_group.append(label.Label(terminalio.FONT, text="Hello World", color=GREEN, scale=4, x=20, y=140))
text_group.append(label.Label(terminalio.FONT, text="Hello World", color=CYAN, scale=6, x=20, y=250))

# --- Screen 3: the shapes -----------------------------------------------
shapes_group = displayio.Group()
shapes_group.append(Rect(40, 50, 140, 100, fill=RED))
shapes_group.append(Circle(300, 100, 55, fill=GREEN))
shapes_group.append(RoundRect(40, 200, 140, 90, 20, fill=BLUE))
shapes_group.append(Triangle(240, 290, 360, 290, 300, 190, fill=YELLOW))

# --- Screen 4: the prompt -----------------------------------------------
prompt_group = displayio.Group()
prompt_group.append(label.Label(terminalio.FONT, text="Press somewhere",
                                color=WHITE, scale=3, x=100, y=160))

# --- Screen 5: the coordinates ------------------------------------------
# This label is kept in its own variable because, unlike everything above,
# its text gets changed later while the program is running.
coords_group = displayio.Group()
coords_label = label.Label(terminalio.FONT, text="", color=YELLOW, scale=3, x=100, y=160)
coords_group.append(coords_label)

# --- The list of screens ------------------------------------------------
# Putting the groups in a list lets us step through them by number instead
# of writing a separate if-statement for each one.
# coords_group is listed TWICE on purpose. That makes the coordinates screen
# take two presses to get past: the first press shows your coordinates, the
# second updates them, and the press after that goes back to the image.
screens = [image_group, text_group, shapes_group,
           prompt_group, coords_group, coords_group]

index = 0                          # which screen we're on right now
display.root_group = screens[index]

# --- Main loop ----------------------------------------------------------
# touch_state remembers whether a finger was already down last time around.
# Without it, one slow press would count as hundreds of presses, because
# this loop runs thousands of times per second.
touch_state = False

while True:

    # A finger just landed - this is one new press
    if tsc.touched and not touch_state:
        touch_state = True

        # Record where the press happened. Every press updates this, so the
        # coordinates screen always shows your most recent press.
        point = tsc.touch
        coords_label.text = "X: %d  Y: %d" % (point["x"], point["y"])
        print("Touch at:", point["x"], point["y"])

        # Move to the next screen. The % wraps back to 0 after the last one,
        # so the coordinates screen leads back around to the image.
        index = (index + 1) % len(screens)
        display.root_group = screens[index]

    # The finger lifted - get ready for the next press
    if not tsc.touched and touch_state:
        touch_state = False
