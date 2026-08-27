# SPDX-License-Identifier: Unlicense
#
# AI-assisted: "Claude (Anthropic)", August 2026
# Human contribution: idea / circuit design / pin mapping / debugging / testing on hardware
# Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

# NYT most-popular headlines on the 3.5" TFT FeatherWing — CircuitPython 10
# /lib needs: adafruit_display_text, adafruit_hx8357,
# adafruit_connection_manager, adafruit_requests

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

SSID = os.getenv("WIFI_SSID_1")
PASSWORD = os.getenv("WIFI_PASSWORD_1")
URL = (
    "https://api.nytimes.com/svc/mostpopular/v2/viewed/1.json"
    f"?api-key={os.getenv('NYT_API_KEY')}"
)

# NYT free tier: 500 calls/day. 86400 sec / 500 = 172.8, so 180 is the floor.
# 300 gives 288 calls/day — room for reboots and retries.
SLEEP_SECONDS = 300

displayio.release_displays()
display = adafruit_hx8357.HX8357(
    fourwire.FourWire(board.SPI(), command=board.D10, chip_select=board.D9),
    width=480,
    height=320,
)

text = label.Label(
    terminalio.FONT, text="connecting", color=0xFF00FF, scale=3,
    background_color=0x000000, line_spacing=1.3, x=15, y=50,
)
display.root_group = text


def wrap(headline, max_chars=26):
    """Break a headline onto lines at spaces. 26 chars fits 480px at scale 3."""
    lines, line = [], ""
    for word in headline.split():
        if len((line + " " + word).strip()) <= max_chars:
            line = (line + " " + word).strip()
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return "\n".join(lines)


wifi.radio.connect(SSID, PASSWORD)
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)

index = 0

while True:
    try:
        if not wifi.radio.connected:  # reconnect after a router blip
            wifi.radio.connect(SSID, PASSWORD)
        with requests.get(URL) as response:
            stories = response.json()["results"]
        headline = stories[index % len(stories)]["title"]  # step through in order
        index += 1
        print(headline)
        text.text = wrap(headline)
    except Exception as err:
        # KeyError: results usually means HTTP 429 — over the daily quota
        print("failed:", err)
        text.text = "offline"
    time.sleep(SLEEP_SECONDS)
