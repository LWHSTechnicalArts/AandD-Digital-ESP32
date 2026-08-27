# SPDX-License-Identifier: Unlicense
# AI-assisted: "Claude (Anthropic)", August 2026
# Human contribution: idea / circuit design / pin mapping / debugging / testing on hardware
# Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

# SHT4x temperature + humidity on the 3.5" TFT FeatherWing V2
# Save on the CIRCUITPY drive as code.py
# Needs adafruit_display_text, adafruit_hx8357, adafruit_sht4x,
# and adafruit_bus_device in the /lib folder
import time
import board
import displayio
import fourwire
import terminalio                        # the built-in font
import adafruit_hx8357
import adafruit_sht4x
from adafruit_display_text import label

# --- Set up the screen (same as before) ---------------------------------
displayio.release_displays()
spi = board.SPI()
display_bus = fourwire.FourWire(spi, command=board.D10, chip_select=board.D9)
display = adafruit_hx8357.HX8357(display_bus, width=480, height=320)

# --- Set up the sensor --------------------------------------------------
# The FeatherWing uses SPI, the sensor uses I2C, so they don't conflict.
i2c = board.STEMMA_I2C()
sht = adafruit_sht4x.SHT4x(i2c)
sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
print("Serial number:", hex(sht.serial_number))

# --- Colors -------------------------------------------------------------
WHITE = 0xFFFFFF
ORANGE = 0xFF8800
CYAN = 0x00FFFF

# --- Make the text ------------------------------------------------------
# The readings start as placeholders and get filled in by the loop below.
title = label.Label(terminalio.FONT, text="SHT4x Sensor", color=WHITE, scale=3, x=20, y=40)
temp_label = label.Label(terminalio.FONT, text="--.- C", color=ORANGE, scale=6, x=20, y=140)
hum_label = label.Label(terminalio.FONT, text="--.- %", color=CYAN, scale=6, x=20, y=240)

# --- Put it on screen ---------------------------------------------------
group = displayio.Group()
group.append(title)
group.append(temp_label)
group.append(hum_label)
display.root_group = group

# --- Read and update once a second --------------------------------------
while True:
    temperature, relative_humidity = sht.measurements

    # Changing .text redraws just that label - the rest of the screen
    # stays put, so there's no flicker.
    temp_label.text = f"{temperature:.1f} C"
    hum_label.text = f"{relative_humidity:.1f} %"

    print(f"Temp: {temperature:.1f} C   Humidity: {relative_humidity:.1f} %")
    time.sleep(1)
