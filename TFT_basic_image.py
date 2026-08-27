# SPDX-License-Identifier: Unlicense
#
# AI-assisted: "Claude (Anthropic)", August 2026
# Human contribution: idea / circuit design / pin mapping / debugging / testing on hardware
# Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

# Show a single image on the 3.5" TFT FeatherWing V2
# Save on the CIRCUITPY drive as code.py
# Put image.bmp in the top level of the CIRCUITPY drive
 
import board
import displayio
import fourwire
import adafruit_hx8357
 
# Let go of any display that was already set up
displayio.release_displays()
 
# Set up the screen
spi = board.SPI()
display_bus = fourwire.FourWire(spi, command=board.D10, chip_select=board.D9)
display = adafruit_hx8357.HX8357(display_bus, width=480, height=320)
 
# Load the image and wrap it in a TileGrid so displayio can place it
bitmap = displayio.OnDiskBitmap("/image.bmp")
tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
 
# A Group holds everything on screen. Ours holds just the one image.
group = displayio.Group()
group.append(tile_grid)
display.root_group = group
 
# Keep the program running so the image stays up
while True:
    pass
 
