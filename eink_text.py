# SPDX-License-Identifier: Unlicense
#
# AI-assisted: "Claude (Anthropic)", August 2026
# Human contribution: circuit design / pin mapping / debugging / testing on hardware
# Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

"""Minimal eInk test: prints "Hello dolphin" on the screen.
Needs the adafruit_display_text library in /lib on CIRCUITPY.
"""

import time
import board
import displayio
import terminalio
from adafruit_display_text import label
from fourwire import FourWire
import adafruit_ssd1680

displayio.release_displays()

spi = board.SPI()
epd_cs = board.D9
epd_dc = board.D10
epd_reset = None
epd_busy = None

display_bus = FourWire(
    spi, command=epd_dc, chip_select=epd_cs, reset=epd_reset, baudrate=1000000
)

display = adafruit_ssd1680.SSD1680(
    display_bus,
    width=250,
    height=122,
    busy_pin=epd_busy,
    highlight_color=0xFF0000,
    rotation=270,  # Try 0 for a wide screen instead of a tall one
    colstart=0,  # Comment out for older displays
)

hello = label.Label(
    terminalio.FONT,
    text="Hello",
    color=0x000000,
    scale=4,
    anchor_point=(0.5, 0.5),
    anchored_position=(display.width // 2, display.height // 2 - 20),
)

dolphin = label.Label(
    terminalio.FONT,
    text="dolphin",
    color=0xFF0000,
    scale=4,
    anchor_point=(0.5, 0.5),
    anchored_position=(display.width // 2, display.height // 2 + 20),
)

group = displayio.Group()

bg_palette = displayio.Palette(1)
bg_palette[0] = 0xFFFFFF
group.append(
    displayio.TileGrid(
        displayio.Bitmap(display.width, display.height, 1), pixel_shader=bg_palette
    )
)
group.append(hello)
group.append(dolphin)
display.root_group = group

display.refresh()
print("refreshed")

while True:
    pass # your additional code here
