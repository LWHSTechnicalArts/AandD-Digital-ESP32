# SPDX-License-Identifier: MIT
"""Open-Meteo weather on an SSD1680 eInk — CircuitPython 9/10, Feather ESP32-S3.
Data by Open-Meteo.com, CC BY 4.0. No API key required.
Created in collaboration with Claude
"""

import os
import time

import board
import displayio
import terminalio
import wifi
from adafruit_display_text import label
from fourwire import FourWire

import adafruit_connection_manager
import adafruit_requests
import adafruit_ssd1680

# ----------------------------------------------------------------- config

LAT = os.getenv("WEATHER_LAT")
LON = os.getenv("WEATHER_LON")
PLACE = os.getenv("WEATHER_PLACE")
SSID = os.getenv("WIFI_SSID_1")
PASSWORD = os.getenv("WIFI_PASSWORD_1")

for name, value in (("WEATHER_LAT", LAT), ("WEATHER_LON", LON),
                    ("WEATHER_PLACE", PLACE), ("WIFI_SSID_1", SSID)):
    if not value:
        raise RuntimeError(f"{name} missing from settings.toml — hard-reset after editing")

URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
    "&temperature_unit=fahrenheit"
    "&wind_speed_unit=mph"
)

POLL_SECONDS = 600
REFRESH_SECONDS = 20  # panel needs this undisturbed; raise to 30 if it stalls

CONDITIONS = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "violent showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorms", 96: "storms with hail", 99: "severe hailstorms",
}

BLACK = 0x000000
RED = 0xFF0000
WHITE = 0xFFFFFF

CHAR_WIDTH = 6  # terminalio.FONT is a fixed 6px per character at scale 1


def wrap(text, max_chars):
    """Break text onto multiple lines at spaces, for narrow labels."""
    lines, line = [], ""
    for word in text.split(" "):
        candidate = (line + " " + word).strip()
        if len(candidate) <= max_chars:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word[:max_chars]
    if line:
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------- display

displayio.release_displays()

display_bus = FourWire(
    board.SPI(),
    command=board.D10,
    chip_select=board.D9,
    reset=None,
    baudrate=1000000,
)

display = adafruit_ssd1680.SSD1680(
    display_bus,
    width=250,
    height=122,
    busy_pin=None,
    highlight_color=RED,
    rotation=270,
    colstart=0,
)

# Never assume which way rotation reports these — read them and lay out to fit
W, H = display.width, display.height
print(f"Drawing area is {W} x {H}")

CENTER = W // 2
MAX_CHARS = W // (CHAR_WIDTH * 2)  # characters per line at scale 2
TEMP_SCALE = 4 if W >= 4 * 4 * CHAR_WIDTH else 3  # shrink if the panel is narrow

place_label = label.Label(
    terminalio.FONT, text="", color=BLACK, scale=2, line_spacing=1.2,
    anchor_point=(0.5, 0.5), anchored_position=(CENTER, int(H * 0.14)),
)
temp_label = label.Label(
    terminalio.FONT, text="--", color=RED, scale=TEMP_SCALE,
    anchor_point=(0.5, 0.5), anchored_position=(CENTER, int(H * 0.42)),
)
sky_label = label.Label(
    terminalio.FONT, text="starting", color=BLACK, scale=2, line_spacing=1.2,
    anchor_point=(0.5, 0.5), anchored_position=(CENTER, int(H * 0.67)),
)
detail_label = label.Label(
    terminalio.FONT, text="", color=BLACK, scale=1, line_spacing=1.4,
    anchor_point=(0.5, 0.5), anchored_position=(CENTER, int(H * 0.90)),
)

group = displayio.Group()
bg_palette = displayio.Palette(1)
bg_palette[0] = WHITE
group.append(
    displayio.TileGrid(displayio.Bitmap(W, H, 1), pixel_shader=bg_palette)
)
for item in (place_label, temp_label, sky_label, detail_label):
    group.append(item)
display.root_group = group


def refresh():
    """Redraw and block until the panel has actually finished."""
    while display.time_to_refresh > 0:
        time.sleep(display.time_to_refresh + 0.5)
    display.refresh()
    time.sleep(REFRESH_SECONDS)


# ---------------------------------------------------------------- network

print("Connecting to", SSID)
if not wifi.radio.connected:
    wifi.radio.connect(SSID, PASSWORD)
print("Connected. IP:", wifi.radio.ipv4_address)

pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)

last_shown = None

while True:
    try:
        if not wifi.radio.connected:
            wifi.radio.connect(SSID, PASSWORD)
            print("Reconnected. IP:", wifi.radio.ipv4_address)

        with requests.get(URL) as response:
            current = response.json()["current"]

        temperature = round(current["temperature_2m"])
        humidity = current["relative_humidity_2m"]
        wind = round(current["wind_speed_10m"])
        sky = CONDITIONS.get(current["weather_code"], "unknown")

        print(f"It's currently {temperature} degrees and {sky} in {PLACE}.")
        print(f"  Humidity {humidity}%, wind {wind} mph")

        reading = (temperature, humidity, wind, sky)
        if reading != last_shown:
            place_label.text = wrap(PLACE, MAX_CHARS)
            temp_label.text = f"{temperature}F"
            sky_label.text = wrap(sky, MAX_CHARS)
            detail_label.text = f"{humidity}% humidity\n{wind} mph wind"
            print(f"  sky_label at y={sky_label.anchored_position[1]} of {H}")
            refresh()
            last_shown = reading
            print("  screen updated")
        else:
            print("  unchanged, skipping redraw")

    except Exception as err:
        print("Fetch failed:", err)
        if sky_label.text != "offline":
            sky_label.text = "offline"
            refresh()
            last_shown = None

    time.sleep(POLL_SECONDS)
