# ChunkFive font demo on the 3.5" TFT FeatherWing V2
# Save on the CIRCUITPY drive as code.py
# Needs adafruit_display_text, adafruit_bitmap_font, adafruit_hx8357,
# and font_chunk_five_regular_24 in /lib
# created in collaboration with Claude

import board
import displayio
import fourwire
import terminalio
import adafruit_hx8357
from adafruit_display_text import label
from font_chunk_five_regular_48 import FONT as CHUNK

# --- Set up the screen (same as before) ---------------------------------
displayio.release_displays()
spi = board.SPI()
display_bus = fourwire.FourWire(spi, command=board.D10, chip_select=board.D9)
display = adafruit_hx8357.HX8357(display_bus, width=480, height=320)

# --- Make the text ------------------------------------------------------
plain = label.Label(terminalio.FONT, text="Hello Toads!", color=0x666666, scale=2, x=20, y=50)
chunky = label.Label(CHUNK, text="Hello Toads!", color=0xFFAA00, scale=1, x=20, y=150)
big = label.Label(CHUNK, text="TOADS", color=0x00FF88, scale=2, x=20, y=250)

group = displayio.Group()
group.append(plain)
group.append(chunky)
group.append(big)
display.root_group = group

while True:
    pass
