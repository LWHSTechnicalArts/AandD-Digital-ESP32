# SPDX-License-Identifier: Unlicense
#
# AI-assisted: "Claude (Anthropic)", August 2026
# Human contribution: idea / circuit design / pin mapping / debugging / testing on hardware
# Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

# Time and date on the 3.5" TFT FeatherWing V2
# Works with CircuitPython 10
# /lib: adafruit_display_text, adafruit_ds3231, adafruit_bus_device,
#       adafruit_hx8357

import time
import board
import displayio
import fourwire
import terminalio
import adafruit_hx8357
import adafruit_ds3231
from adafruit_display_text import bitmap_label

# --- Screen -------------------------------------------------------------
displayio.release_displays()
spi = board.SPI()
display_bus = fourwire.FourWire(spi, command=board.D10, chip_select=board.D9)
display = adafruit_hx8357.HX8357(display_bus, width=480, height=320)
# On a board with a built-in screen, delete the four lines above and use:
#   display = board.DISPLAY

# --- Clock --------------------------------------------------------------
i2c = board.I2C()          # or board.STEMMA_I2C() for the JST connector
rtc = adafruit_ds3231.DS3231(i2c)

yellowy = 0x99FF22
days = ("Sunday", "Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday")

if False:   # change to True if you want to write the time!
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    t = time.struct_time((2026,  8,   18,   13,  48,  00,    2,   -1,    -1))
    print("Setting time to:", t)
    rtc.datetime = t

# --- Build the label ONCE -----------------------------------------------
text_area = bitmap_label.Label(terminalio.FONT, text="", scale=3, color=yellowy)
text_area.anchor_point = (0, 0)      # top-left of the label...
text_area.anchored_position = (10, 20)   # ...goes here

group = displayio.Group()
group.append(text_area)
display.root_group = group

# --- Update only when the second actually changes -----------------------
last_second = -1

while True:
    t = rtc.datetime

    if t.tm_sec != last_second:
        last_second = t.tm_sec

        text_area.text = (
            f"{days[t.tm_wday]}\n"
            f"{t.tm_mon}/{t.tm_mday}/{t.tm_year}\n"
            f"{t.tm_hour}:{t.tm_min:02}:{t.tm_sec:02}"
        )

        print(text_area.text.replace("\n", "  "))

    time.sleep(0.1)   # poll ten times a second, redraw once
