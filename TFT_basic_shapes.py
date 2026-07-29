# Four colored shapes on the 3.5" TFT FeatherWing V2
# Save on the CIRCUITPY drive as code.py
# Needs adafruit_display_shapes in the /lib folder

import board
import displayio
import fourwire
import adafruit_hx8357
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.triangle import Triangle

# --- Set up the screen (same as before) ---------------------------------
displayio.release_displays()
spi = board.SPI()
display_bus = fourwire.FourWire(spi, command=board.D10, chip_select=board.D9)
display = adafruit_hx8357.HX8357(display_bus, width=480, height=320)

# --- Colors -------------------------------------------------------------
RED = 0xFF0000
GREEN = 0x00FF00
BLUE = 0x0000FF
YELLOW = 0xFFFF00

# --- Make the shapes ----------------------------------------------------
# Every shape needs a position, a size, and a fill color. The numbers are
# all in pixels, counted from the top-left corner of the screen.

# Rect: x, y of the top-left corner, then width and height
square = Rect(40, 50, 140, 100, fill=RED)

# Circle: x, y of the CENTER, then the radius
circle = Circle(300, 100, 55, fill=GREEN)

# RoundRect: same as Rect, plus how rounded the corners are
rounded = RoundRect(40, 200, 140, 90, 20, fill=BLUE)

# Triangle: the x, y of each of its three corners
triangle = Triangle(240, 290, 360, 290, 300, 190, fill=YELLOW)

# --- Put them on screen -------------------------------------------------
group = displayio.Group()
group.append(square)
group.append(circle)
group.append(rounded)
group.append(triangle)

display.root_group = group

# Keep the program running so the shapes stay up
while True:
    pass
