# Spotify "Now Playing" display
# Shows the album cover, song, artist and album.
# AI-assisted: "Claude (Anthropic)", November 2026
# Human contribution: idea / circuit design / pin mapping / debugging / testing on hardware
# Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

import os
import time

import adafruit_hx8357
import adafruit_requests
import board
import displayio
import jpegio
import socketpool
import ssl
import terminalio
import wifi
from adafruit_display_text import label, wrap_text_to_lines
from fourwire import FourWire

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")
NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"


def b64(text):
    """Base64-encodes text (CircuitPython has no base64 module)."""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    data = text.encode()
    out = ""
    for i in range(0, len(data), 3):
        chunk = data[i : i + 3]
        n = int.from_bytes(chunk + b"\0" * (3 - len(chunk)), "big")
        for j in range(4):
            out += chars[(n >> (18 - 6 * j)) & 63] if j <= len(chunk) else "="
    return out


# ---- Screen ----
displayio.release_displays()
bus = FourWire(board.SPI(), command=board.D10, chip_select=board.D9)
display = adafruit_hx8357.HX8357(bus, width=480, height=320)
screen = displayio.Group()
display.root_group = screen

art = displayio.Group(x=10, y=10)  # album cover goes here
screen.append(art)


def text_label(scale, color, y):
    lbl = label.Label(terminalio.FONT, text="", color=color, scale=scale,
                      anchor_point=(0, 0), anchored_position=(320, y))
    screen.append(lbl)
    return lbl


song_label = text_label(2, 0xFFFFFF, 10)
artist_label = text_label(2, 0xC0C0C0, 110)
album_label = text_label(1, 0x808080, 185)


def wrap(text, max_chars, max_lines):
    return "\n".join(wrap_text_to_lines(text, max_chars)[:max_lines])


# ---- Wi-Fi ----
wifi.radio.connect(os.getenv("WIFI_SSID_1"), os.getenv("WIFI_PASSWORD_1"))
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())


# ---- Spotify ----
def get_access_token():
    headers = {
        "Authorization": "Basic " + b64(CLIENT_ID + ":" + CLIENT_SECRET),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    body = "grant_type=refresh_token&refresh_token=" + REFRESH_TOKEN
    with requests.post("https://accounts.spotify.com/api/token",
                       data=body, headers=headers) as resp:
        return resp.json()["access_token"]


def show_album_cover(url):
    while len(art):
        art.pop()  # remove the old cover
    with requests.get(url) as resp:
        jpeg = resp.content
    decoder = jpegio.JpegDecoder()
    width, height = decoder.open(jpeg)
    bitmap = displayio.Bitmap(width, height, 65535)
    decoder.decode(bitmap)
    art.append(displayio.TileGrid(
        bitmap,
        pixel_shader=displayio.ColorConverter(
            input_colorspace=displayio.Colorspace.RGB565_SWAPPED),
    ))


# ---- Main loop ----
token = get_access_token()
token_time = time.monotonic()
last_song = None

while True:
    try:
        if time.monotonic() - token_time > 3000:  # tokens last 1 hour
            token = get_access_token()
            token_time = time.monotonic()

        with requests.get(NOW_PLAYING_URL,
                          headers={"Authorization": "Bearer " + token}) as resp:
            playing = resp.json() if resp.status_code == 200 else None

        item = playing.get("item") if playing else None
        if item:
            song_id = item.get("id") or item["name"]
            if song_id != last_song:  # only redraw when the song changes
                last_song = song_id
                song_label.text = wrap(item["name"], 12, 3)
                artist_label.text = wrap(", ".join(a["name"] for a in item["artists"]), 12, 2)
                album_label.text = wrap(item["album"]["name"], 25, 4)
                for image in item["album"]["images"]:
                    if image["width"] == 300:  # the 300x300 cover fits the screen
                        show_album_cover(image["url"])
                        break
    except (OSError, RuntimeError, ValueError) as e:
        print("Error:", e)  # network hiccup; try again next time

    time.sleep(5)
