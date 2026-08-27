# SPDX-License-Identifier: Unlicense
# AI-assisted: "Claude (Anthropic)", August 2026
# Human contribution: idea / circuit design / pin mapping / debugging / testing on hardware
# Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

"""Minimal eInk test: prints "Hello dolphin" on the screen.

"Hello" is drawn in black and "dolphin" in red, on a white background.
Needs the adafruit_display_text library in /lib on CIRCUITPY.
"""

import time

import board  # Pin names for whatever board you're running on
import displayio  # CircuitPython's built-in graphics system
import terminalio  # Supplies the built-in bitmap font
from adafruit_display_text import label  # Turns a string into something drawable
from fourwire import FourWire  # The 4-wire SPI protocol the panel speaks

import adafruit_ssd1680  # Driver for this panel's controller chip

# Frees the display hardware in case a previous script left it claimed.
# Without this you get a "Display limit reached" error on the second run.
displayio.release_displays()

# --- Wiring -----------------------------------------------------------
# SPI is the bus that carries pixel data to the panel. The extra pins are
# side-channels the panel needs on top of that bus.
spi = board.SPI()  # Uses the board's standard SCK and MOSI pins
epd_cs = board.D9  # Chip select: "this message is for you, display"
epd_dc = board.D10  # Data/command: is this byte an instruction or pixels?
epd_reset = None  # Hardware reset line; None on the FeatherWing
epd_busy = None  # "Still refreshing" line; None on the FeatherWing

# Bundles the pins into one object the driver can talk through.
# baudrate is the SPI clock speed; 1 MHz is a safe, well-tested value.
display_bus = FourWire(
    spi, command=epd_dc, chip_select=epd_cs, reset=epd_reset, baudrate=1000000
)

# --- The display ------------------------------------------------------
display = adafruit_ssd1680.SSD1680(
    display_bus,
    width=250,  # Panel's native size, before rotation
    height=122,
    busy_pin=epd_busy,  # With None, the driver just waits a fixed time instead
    highlight_color=0xFF0000,  # The third pigment in this panel is red
    rotation=270,  # 270 = tall/portrait. Use 0 for wide/landscape.
    colstart=0,  # 0 for this panel; -8 speckles the bottom edge
)

# --- The text ---------------------------------------------------------
# anchor_point picks a spot on the label itself, as a fraction of its size:
# (0.5, 0.5) is its center, (0, 0) its top-left. anchored_position is where
# on the screen that spot lands. Together they center text without math.
#
# display.width and display.height are read back from the display because
# rotation=270 swaps them: the canvas is 122 wide by 250 tall, not 250x122.
hello = label.Label(
    terminalio.FONT,
    text="Hello",
    color=0x000000,  # Black
    scale=4,  # The font is tiny, so multiply every pixel by 4
    anchor_point=(0.5, 0.5),
    anchored_position=(display.width // 2, display.height // 2 - 20),  # 20px up
)

# A Label is a single color throughout, so a second color means a second
# Label. Only 0x000000, 0xFFFFFF and 0xFF0000 work here -- the panel has
# three pigments and nothing in between.
dolphin = label.Label(
    terminalio.FONT,
    text="dolphin",
    color=0xFF0000,  # Red
    scale=4,
    anchor_point=(0.5, 0.5),
    anchored_position=(display.width // 2, display.height // 2 + 20),  # 20px down
)

# --- Assembling the screen --------------------------------------------
# A Group is a stack of things to draw. Items added later sit on top.
group = displayio.Group()

# A solid white background. A Palette is a lookup table of colors, and a
# Bitmap is a grid of indexes into it -- here every pixel is index 0, white.
# This gets added first so it sits behind the text, and it guarantees every
# pixel on the panel is painted rather than left holding its old image.
bg_palette = displayio.Palette(1)
bg_palette[0] = 0xFFFFFF
group.append(
    displayio.TileGrid(
        displayio.Bitmap(display.width, display.height, 1), pixel_shader=bg_palette
    )
)

# Now the text, on top of the background
group.append(hello)
group.append(dolphin)

# Hand the finished group to the display. Nothing is sent to the panel yet.
display.root_group = group

# This is the step that actually moves the pigment. It takes several
# seconds and is the only part that draws real power.
display.refresh()
print("refreshed")

# eInk holds the image with no power, so there's nothing left to do.
# If you add code below that calls display.refresh() again, you must wait
# display.time_to_refresh seconds first or the driver raises an error.
while True:
    pass  # your additional code here
