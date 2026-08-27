# SPDX-License-Identifier: Unlicense
# AI-assisted: "Claude (Anthropic)", August 2026
# Human contribution: idea / circuit design / pin mapping / debugging / testing on hardware
# Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

# Muni arrivals on the 3.5" TFT FeatherWing — CircuitPython 10
# /lib needs: adafruit_display_text, adafruit_hx8357,
#             adafruit_connection_manager, adafruit_requests

import os
import time

import board
import displayio
import fourwire
import terminalio
import wifi
from adafruit_display_text import label

import adafruit_connection_manager
import adafruit_hx8357
import adafruit_requests

URL = (
    "https://webservices.umoiq.com/api/pub/v1/agencies/sfmta-cis"
    f"/stopcodes/13548/predictions?key={os.getenv('UMOIQ_API_KEY')}"
)

displayio.release_displays()
display = adafruit_hx8357.HX8357(
    fourwire.FourWire(board.SPI(), command=board.D10, chip_select=board.D9),
    width=480,
    height=320,
)

# One label, built once. Only .text changes from here on.
text = label.Label(
    terminalio.FONT, text="connecting", color=0x00FFFF, scale=3,
    background_color=0x000000, x=20, y=40,
)
display.root_group = text

wifi.radio.connect(os.getenv("WIFI_SSID_1"), os.getenv("WIFI_PASSWORD_1"))
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)

while True:
    try:
        with requests.get(URL) as response:
            bus = response.json()[0]  # .json() once — each call is a fetch
        minutes = [v["minutes"] for v in bus["values"]]
        text.text = (
            f"{bus['route']['title']}\n{bus['stop']['name']}\n\n{minutes[0]} min"
            if minutes
            else "no buses right now"
        )
        print(text.text.replace("\n", " "))
    except Exception as err:
        print("failed:", err)
        text.text = "offline"
    time.sleep(15)
