# SPDX-License-Identifier: Unlicense
# AI-assisted: "Claude (Anthropic)", August 2026
# Human contribution: idea / circuit design / pin mapping / debugging / testing on hardware
# Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

"""Current weather from Open-Meteo — CircuitPython 9/10, Feather ESP32-S3.
Data by Open-Meteo.com, CC BY 4.0. No API key required.
Created in collaboration with Claude
"""

import os
import time

import wifi
import adafruit_connection_manager
import adafruit_requests

# Everything configurable lives in settings.toml
LAT = os.getenv("WEATHER_LAT")
LON = os.getenv("WEATHER_LON")
PLACE = os.getenv("WEATHER_PLACE")  # Open-Meteo doesn't return a place name

URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
    "&temperature_unit=fahrenheit"
    "&wind_speed_unit=mph"
)

POLL_SECONDS = 600  # models refresh hourly; 10 min is plenty

# WMO weather codes -> text. Trimmed to the common groups to save RAM.
CONDITIONS = {
    0: "clear",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light showers",
    81: "showers",
    82: "violent showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorms",
    96: "thunderstorms with hail",
    99: "severe thunderstorms with hail",
}

# The connection manager pools sockets and hands back an SSL context
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)

while True:
    try:
        # CircuitPython joins the network at boot; this is the reconnect path
        if not wifi.radio.connected:
            wifi.radio.connect(
                os.getenv("WIFI_SSID_1"),
                os.getenv("WIFI_PASSWORD_1"),
            )
            print("Reconnected. IP:", wifi.radio.ipv4_address)

        # "with" closes the response and frees the socket
        with requests.get(URL) as response:
            current = response.json()["current"]

        temperature = current["temperature_2m"]
        humidity = current["relative_humidity_2m"]
        wind = current["wind_speed_10m"]
        sky = CONDITIONS.get(current["weather_code"], "unknown conditions")

        print(f"It's currently {temperature} degrees and {sky} in {PLACE}.")
        print(f"  Humidity {humidity}%, wind {wind} mph")

    except Exception as err:  # keep the loop alive through wifi hiccups
        print("Fetch failed:", err)

    time.sleep(POLL_SECONDS)
