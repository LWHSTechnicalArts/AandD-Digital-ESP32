# SPDX-License-Identifier: Unlicense
# AI-assisted: "Claude (Anthropic)", August 2026
# Human contribution: idea / circuit design / pin mapping / debugging / testing on hardware
# Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

# Weather + Groq clothing advice on the 3.5" TFT FeatherWing — CircuitPython 10
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

SSID = os.getenv("WIFI_SSID_1")
PASSWORD = os.getenv("WIFI_PASSWORD_1")
GROQ_KEY = os.getenv("GROQ_API_KEY")

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={os.getenv('WEATHER_LAT')}&longitude={os.getenv('WEATHER_LON')}"
    "&current=temperature_2m,wind_speed_10m,weather_code"
    "&temperature_unit=fahrenheit&wind_speed_unit=mph"
)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SLEEP_SECONDS = 900  # 15 min — weather barely moves faster than that

CONDITIONS = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "light showers", 81: "showers", 82: "heavy showers",
    95: "thunderstorms",
}

displayio.release_displays()
display = adafruit_hx8357.HX8357(
    fourwire.FourWire(board.SPI(), command=board.D10, chip_select=board.D9),
    width=480,
    height=320,
)

weather_text = label.Label(
    terminalio.FONT, text="connecting", color=0x00FFFF, scale=3,
    background_color=0x000000, x=15, y=40,
)
advice_text = label.Label(
    terminalio.FONT, text="", color=0xFFFFFF, scale=2,
    background_color=0x000000, line_spacing=1.4, x=15, y=120,
)
group = displayio.Group()
group.append(weather_text)
group.append(advice_text)
display.root_group = group


def wrap(sentence, max_chars=40):
    """Break text onto lines at spaces. 40 chars fits 480px at scale 2."""
    lines, line = [], ""
    for word in sentence.split():
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

while True:
    try:
        if not wifi.radio.connected:
            wifi.radio.connect(SSID, PASSWORD)

        # 1. What's the weather?
        with requests.get(WEATHER_URL) as response:
            now = response.json()["current"]
        temp = round(now["temperature_2m"])
        wind = round(now["wind_speed_10m"])
        sky = CONDITIONS.get(now["weather_code"], "unclear skies")

        # 2. Ask Groq what to wear
        body = {
            "model": "openai/gpt-oss-20b",  # Groq retired the Llama chat models
            "messages": [{
                "role": "user",
                "content": (
                    f"It is {temp}F, {sky}, wind {wind} mph. "
                    "Give clothing advice in exactly 2 short sentences. "
                    "Plain text only, no bullet points."
                ),
            }],
            "max_completion_tokens": 300,  # room for the model to think
            "reasoning_effort": "low",
        }
        headers = {"Authorization": f"Bearer {GROQ_KEY}"}
        with requests.post(GROQ_URL, json=body, headers=headers) as response:
            advice = response.json()["choices"][0]["message"]["content"].strip()

        print(f"{temp}F, {sky}\n{advice}")
        weather_text.text = f"{temp}F {sky}"
        advice_text.text = wrap(advice)

    except Exception as err:
        print("failed:", err)
        weather_text.text = "offline"

    time.sleep(SLEEP_SECONDS)
