# Show a single image on the 3.5" TFT FeatherWing V2
# Save on the CIRCUITPY drive as code.py
# Put image.bmp in the top level of the CIRCUITPY drive (not in a folder)

# --- Libraries ----------------------------------------------------------
import board             # names for the physical pins on this board
import displayio         # CircuitPython's system for drawing on screens
import fourwire          # the wiring style this screen uses to talk to the board
import adafruit_hx8357   # the driver for this specific screen's chip

# --- Set up the screen --------------------------------------------------
# Clear out any display setup left over from a previous run. Without this
# you get an error saying the pins are already in use when you re-save.
displayio.release_displays()

# SPI is the "language" the board and screen use to talk. It needs three
# shared wires, and board.SPI() hands us the ones already wired on the Feather.
spi = board.SPI()

# Two more pins finish the connection, and these are specific to this screen:
#   command (D10) - tells the screen "this next part is an instruction"
#   chip_select (D9) - tells the screen "I'm talking to YOU right now"
display_bus = fourwire.FourWire(spi, command=board.D10, chip_select=board.D9)

# Now build the actual display object. 480x320 is this screen's size in pixels.
display = adafruit_hx8357.HX8357(display_bus, width=480, height=320)

# --- Load the image -----------------------------------------------------
# OnDiskBitmap reads the image straight off the drive as it draws, instead
# of loading the whole thing into memory. These boards don't have much
# memory, so this is how you show a picture without running out.
bitmap = displayio.OnDiskBitmap("/image.bmp")

# A TileGrid is the wrapper that lets displayio actually place an image
# on the screen. The pixel_shader is the image's own color palette -
# we're just handing the bitmap's colors back to it, unchanged.
tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)

# --- Put it on screen ---------------------------------------------------
# A Group is a container for everything you want visible at once. Later you
# might add text or shapes to the same group. Right now it's just the image.
group = displayio.Group()
group.append(tile_grid)

# root_group is what the screen is currently showing. Setting it displays
# the group - this is the line that actually makes the image appear.
display.root_group = group

# --- Keep it up ---------------------------------------------------------
# When code.py reaches the end, CircuitPython stops the program and clears
# the screen. This loop does nothing forever, which keeps the image visible.
while True:
    pass
