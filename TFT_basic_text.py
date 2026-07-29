# "Hello World" in three sizes and colors on the 3.5" TFT FeatherWing V2
# Save on the CIRCUITPY drive as code.py
# Needs adafruit_display_text in the /lib folder

import board
import displayio
import fourwire
import terminalio                        # the built-in font
import adafruit_hx8357
from adafruit_display_text import label  # makes text you can put on screen

# --- Set up the screen (same as before) ---------------------------------
displayio.release_displays()
spi = board.SPI()
display_bus = fourwire.FourWire(spi, command=board.D10, chip_select=board.D9)
display = adafruit_hx8357.HX8357(display_bus, width=480, height=320)

# --- Colors -------------------------------------------------------------
# On a screen, colors are written as 0xRRGGBB - one hex pair each for
# red, green and blue. It's the same idea as the (255, 0, 0) tuples used
# for NeoPixels, just written differently.
RED = 0xFF0000
GREEN = 0x00FF00
CYAN = 0x00FFFF

# --- Make the text ------------------------------------------------------
# scale makes the letters bigger: 2 is double size, 4 is quadruple.
# At scale 6, "Hello World" nearly fills the width of the screen.
# x and y are where the text sits, in pixels from the top-left corner.
small = label.Label(terminalio.FONT, text="Hello Frogs", color=RED, scale=2, x=20, y=50)
medium = label.Label(terminalio.FONT, text="Hello Toads", color=GREEN, scale=4, x=20, y=140)
large = label.Label(terminalio.FONT, text="Hello Snakes", color=CYAN, scale=6, x=20, y=250)

# --- Put it on screen ---------------------------------------------------
group = displayio.Group()
group.append(small)     # everything added to the group shows up together
group.append(medium)
group.append(large)

display.root_group = group

# Keep the program running so the text stays up
while True:
    pass
