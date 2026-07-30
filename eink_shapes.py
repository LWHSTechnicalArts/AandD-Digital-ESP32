# SPDX-License-Identifier: Unlicense
"""Two different characters side by side: a happy round one on the left,
a sad boxy one on the right.
Needs the adafruit_display_shapes library in /lib on CIRCUITPY.
"""

import time
import board
import displayio
from adafruit_display_shapes.arc import Arc
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.line import Line
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.roundrect import RoundRect
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
    rotation=270,  # Known good on this panel. 0 and 180 refresh only half.
    colstart=0,
)

print("canvas is", display.width, "x", display.height)

BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

STROKE = 3  # Line weight, used everywhere
R = 28  # Head radius. Two of these plus a gap is 122 pixels wide.
MOUTH_R = 14


def thick_line(group, x0, y0, x1, y1, color):
    """Line has no thickness of its own, so stack STROKE of them."""
    for i in range(STROKE):
        group.append(Line(x0, y0 + i, x1, y1 + i, color))


def draw_happy(group, cx, cy):
    """Round head, round eyes, big red smile."""
    group.append(Circle(cx, cy, R, fill=None, outline=BLACK, stroke=STROKE))

    group.append(Circle(cx - 10, cy - 9, 4, fill=BLACK))
    group.append(Circle(cx + 10, cy - 9, 4, fill=BLACK))

    # x and y are the center of the circle the arc belongs to, which sits
    # ABOVE a smile. direction is where the arc's midpoint points, in polar
    # degrees: 0 right, 90 up, 180 left, 270 down. A smile dips downward.
    group.append(
        Arc(
            x=cx,
            y=cy + 2,
            radius=MOUTH_R,
            angle=140,
            direction=270,
            segments=8,
            arc_width=5,
            fill=RED,
        )
    )


def draw_sad(group, cx, cy):
    """Boxy head, square eyes, worried eyebrows, red frown."""
    # RoundRect takes a top-left corner, so shift back by half its size
    group.append(
        RoundRect(cx - R, cy - 27, 2 * R, 54, 10, fill=None, outline=BLACK, stroke=STROKE)
    )

    group.append(Rect(cx - 14, cy - 12, 7, 7, fill=BLACK))
    group.append(Rect(cx + 7, cy - 12, 7, 7, fill=BLACK))

    # Eyebrows tilted up at the inner ends, which is what reads as worried
    thick_line(group, cx - 16, cy - 17, cx - 6, cy - 21, BLACK)
    thick_line(group, cx + 6, cy - 21, cx + 16, cy - 17, BLACK)

    # Same arc, but the center sits BELOW the mouth and the midpoint
    # points up, which flips the curve into a frown.
    group.append(
        Arc(
            x=cx,
            y=cy + 21,
            radius=MOUTH_R,
            angle=140,
            direction=90,
            segments=8,
            arc_width=5,
            fill=RED,
        )
    )


group = displayio.Group()

# White background so every pixel gets painted
bg_palette = displayio.Palette(1)
bg_palette[0] = WHITE
group.append(
    displayio.TileGrid(
        displayio.Bitmap(display.width, display.height, 1), pixel_shader=bg_palette
    )
)

# Left and right, halfway down the tall canvas
draw_happy(group, display.width // 4, display.height // 2)
draw_sad(group, 3 * display.width // 4, display.height // 2)

display.root_group = group

print("refreshing, leave the board alone")
display.refresh()
print("done")

while True:
    pass
