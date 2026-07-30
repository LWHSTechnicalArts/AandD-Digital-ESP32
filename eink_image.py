# SPDX-License-Identifier: Unlicense
"""Displays a full-screen bitmap on the eInk display.

Put a file called image.bmp in the root of CIRCUITPY. At rotation=270 the
canvas is 122 wide by 250 tall, so the bitmap should be 122 x 250.

Save it as an indexed (palette) BMP using only these three colors:
  white  0xFFFFFF
  black  0x000000
  red    0xFF0000
Any other color gets snapped to the nearest of those three.
"""

import time

import board
import displayio
from fourwire import FourWire

import adafruit_ssd1680

FILENAME = "/cat.bmp"

displayio.release_displays()

# Change these pins to match your board
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
    rotation=270,  # Known good on this panel. 0 and 180 refresh only half.
    colstart=0,
)

print("canvas is", display.width, "x", display.height)

# OnDiskBitmap streams the file from flash instead of loading it all into
# RAM, which is what makes full-screen images possible on small boards.
picture = displayio.OnDiskBitmap(FILENAME)
print("bitmap is", picture.width, "x", picture.height)

if (picture.width, picture.height) != (display.width, display.height):
    print("size mismatch -- the image will be cropped or leave gaps")

# The bitmap carries its own palette, so hand that over as the shader
tile = displayio.TileGrid(picture, pixel_shader=picture.pixel_shader)

group = displayio.Group()
group.append(tile)
display.root_group = group

print("refreshing, leave the board alone")
display.refresh()

print("done")

while True:
    pass
