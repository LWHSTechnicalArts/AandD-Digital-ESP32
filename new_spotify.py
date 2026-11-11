# Spotify "Now Playing" display (CircuitPython 9.x)
# Adafruit Feather ESP32-S2 + 3.5" 480x320 TFT FeatherWing (HX8357D)
#
# Libraries needed in CIRCUITPY/lib (from the CircuitPython library bundle,
# or run: circup install adafruit_hx8357 adafruit_requests adafruit_display_text):
#   adafruit_hx8357, adafruit_requests, adafruit_connection_manager,
#   adafruit_display_text
#
# Credentials go in settings.toml.

import gc
import os
import time

import adafruit_hx8357
import adafruit_requests
import board
import displayio
import socketpool
import ssl
import terminalio
import vectorio
import wifi
from adafruit_display_text import label, wrap_text_to_lines

try:
    from fourwire import FourWire  # CircuitPython 9+
except ImportError:
    from displayio import FourWire  # CircuitPython 8

try:
    import jpegio  # album art; not included in every build
except ImportError:
    jpegio = None

# ---------- Settings ----------
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")

TOKEN_URL = "https://accounts.spotify.com/api/token"
# market=from_token drops the long available_markets lists from the response
NOW_PLAYING_URL = (
    "https://api.spotify.com/v1/me/player/currently-playing?market=from_token"
)
POLL_INTERVAL = 5  # seconds

# ---------- Layout ----------
ART_X, ART_Y, ART_SIZE = 10, 10, 300
TEXT_X, TEXT_W = 320, 150
BAR_Y, BAR_H = 280, 8

WHITE = 0xFFFFFF
LIGHT_GRAY = 0xC0C0C0
DIM_GRAY = 0x808080
GREEN = 0x1DB954


def now_ms():
    return time.monotonic_ns() // 1_000_000


def b64encode(text):
    """Small base64 encoder (CircuitPython has no base64 module)."""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    data = text.encode()
    out = ""
    for i in range(0, len(data), 3):
        chunk = data[i : i + 3]
        n = int.from_bytes(chunk + b"\0" * (3 - len(chunk)), "big")
        for j in range(4):
            out += alphabet[(n >> (18 - 6 * j)) & 63] if j <= len(chunk) else "="
    return out
print("token length:", len(refresh_token), "starts:", refresh_token[:4])

# ---------- Display setup ----------
displayio.release_displays()
spi = board.SPI()
bus = FourWire(spi, command=board.D10, chip_select=board.D9)
display = adafruit_hx8357.HX8357(bus, width=480, height=320)

root = displayio.Group()
display.root_group = root

track_group = displayio.Group()
msg_group = displayio.Group()
root.append(track_group)
root.append(msg_group)

art_group = displayio.Group(x=ART_X, y=ART_Y)
track_group.append(art_group)


def make_label(scale, color, y):
    lbl = label.Label(
        terminalio.FONT,
        text="",
        color=color,
        scale=scale,
        line_spacing=1.1,
        anchor_point=(0, 0),
        anchored_position=(TEXT_X, y),
    )
    track_group.append(lbl)
    return lbl


title_lbl = make_label(2, WHITE, 10)
artist_lbl = make_label(2, LIGHT_GRAY, 105)
album_lbl = make_label(1, DIM_GRAY, 175)
status_lbl = make_label(1, GREEN, BAR_Y - 18)
time_lbl = make_label(1, DIM_GRAY, BAR_Y + BAR_H + 6)

bar_palette = displayio.Palette(2)
bar_palette[0] = 0x404040
bar_palette[1] = GREEN
track_group.append(
    vectorio.Rectangle(pixel_shader=bar_palette, color_index=0,
                       width=TEXT_W, height=BAR_H, x=TEXT_X, y=BAR_Y)
)
bar_fill = vectorio.Rectangle(pixel_shader=bar_palette, color_index=1,
                              width=1, height=BAR_H, x=TEXT_X, y=BAR_Y)
track_group.append(bar_fill)

msg_lbl = label.Label(
    terminalio.FONT, text="", color=WHITE, scale=2,
    anchor_point=(0.5, 0.5), anchored_position=(240, 160),
)
msg_group.append(msg_lbl)

# ---------- State ----------
access_token = None
token_expires_ms = 0
current_key = None
current_image = None
is_playing = False
progress_ms = 0
duration_ms = 0
progress_stamp = 0


def show_message(text):
    global current_key, current_image
    current_key = None
    current_image = None
    track_group.hidden = True
    msg_group.hidden = False
    if msg_lbl.text != text:
        msg_lbl.text = text


def wrapped(text, max_chars, max_lines):
    lines = wrap_text_to_lines(text, max_chars)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max_chars - 3] + "..."
    return "\n".join(lines)


def show_placeholder():
    art_group.append(
        vectorio.Rectangle(pixel_shader=bar_palette, color_index=0,
                           width=ART_SIZE, height=ART_SIZE, x=0, y=0)
    )


def show_album_art(url):
    while len(art_group):
        art_group.pop()
    gc.collect()
    if jpegio is None or not url:
        show_placeholder()
        return
    try:
        with requests.get(url) as resp:
            data = resp.content
        decoder = jpegio.JpegDecoder()
        w, h = decoder.open(data)
        scale = 0  # each step halves the size
        while scale < 3 and ((w >> scale) > ART_SIZE or (h >> scale) > ART_SIZE):
            scale += 1
        bw, bh = w >> scale, h >> scale
        bitmap = displayio.Bitmap(bw, bh, 65535)
        decoder.decode(bitmap, scale=scale)
        del data
        art_group.append(
            displayio.TileGrid(
                bitmap,
                pixel_shader=displayio.ColorConverter(
                    input_colorspace=displayio.Colorspace.RGB565_SWAPPED
                ),
                x=(ART_SIZE - bw) // 2,
                y=(ART_SIZE - bh) // 2,
            )
        )
    except (MemoryError, OSError, RuntimeError, ValueError) as e:
        print("Album art failed:", e)
        show_placeholder()


def position_ms():
    pos = progress_ms
    if is_playing:
        pos += now_ms() - progress_stamp
    return min(pos, duration_ms)


def update_progress():
    pos = position_ms()
    filled = max(1, TEXT_W * pos // duration_ms) if duration_ms else 1
    if bar_fill.width != filled:
        bar_fill.width = filled
    secs = pos // 1000
    text = "{}:{:02d} / {}:{:02d}".format(
        secs // 60, secs % 60, duration_ms // 60000, (duration_ms // 1000) % 60
    )
    if time_lbl.text != text:
        time_lbl.text = text
    status = "" if is_playing else "PAUSED"
    if status_lbl.text != status:
        status_lbl.text = status


def refresh_access_token():
    global access_token, token_expires_ms, refresh_token
    headers = {
        "Authorization": "Basic " + b64encode(CLIENT_ID + ":" + CLIENT_SECRET),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    body = "grant_type=refresh_token&refresh_token=" + refresh_token
    with requests.post(TOKEN_URL, data=body, headers=headers) as resp:
        if resp.status_code != 200:
            print("Token refresh failed:", resp.status_code, resp.text)
            return False
        data = resp.json()
    access_token = data["access_token"]
    token_expires_ms = now_ms() + (data.get("expires_in", 3600) - 60) * 1000
    refresh_token = data.get("refresh_token", refresh_token)  # may rotate
    print("Got new access token")
    return True


def poll():
    """Checks Spotify and updates the screen. Returns seconds until next poll."""
    global access_token, current_key, current_image
    global is_playing, progress_ms, duration_ms, progress_stamp

    if access_token is None or now_ms() > token_expires_ms:
        if not refresh_access_token():
            show_message("Spotify login failed\nSee serial console")
            return 30

    data = None
    headers = {"Authorization": "Bearer " + access_token}
    with requests.get(NOW_PLAYING_URL, headers=headers) as resp:
        status = resp.status_code
        if status == 200:
            data = resp.json()
        elif status == 429:
            wait = int(resp.headers.get("retry-after", 5))
            print("Rate limited, waiting", wait, "s")
            return max(wait, 5)

    if status == 204:
        show_message("Nothing playing")
        return POLL_INTERVAL
    if status == 401:
        access_token = None
        return 1
    if status != 200:
        print("currently-playing failed:", status)
        return POLL_INTERVAL

    item = data.get("item")
    if not item:
        show_message("Playing something else\n(podcast or ad)")
        return POLL_INTERVAL

    title = item.get("name", "")
    artists = ", ".join(a.get("name", "") for a in item.get("artists", []))
    album = item.get("album", {})
    images = album.get("images", [])
    image_url = images[0]["url"] if images else None  # largest, gets scaled
    for img in images:
        if img.get("width") == 300:
            image_url = img["url"]
            break

    is_playing = data.get("is_playing", False)
    progress_ms = data.get("progress_ms") or 0
    duration_ms = item.get("duration_ms") or 0
    progress_stamp = now_ms()
    del data
    gc.collect()

    key = item.get("id") or (title + artists)  # local files have no id
    if key != current_key or track_group.hidden:
        current_key = key
        print("Now playing:", artists, "-", title)
        title_lbl.text = wrapped(title, TEXT_W // 12, 3)
        artist_lbl.text = wrapped(artists, TEXT_W // 12, 2)
        album_lbl.text = wrapped(album.get("name", ""), TEXT_W // 6, 3)
        msg_group.hidden = True
        track_group.hidden = False
        if image_url != current_image:  # same album = keep the art
            show_album_art(image_url)
            current_image = image_url

    update_progress()
    return POLL_INTERVAL


def connect_wifi():
    show_message("Connecting to Wi-Fi...")
    while not wifi.radio.connected:
        try:
            wifi.radio.connect(os.getenv("WIFI_SSID_1"),
                               os.getenv("WIFI_PASSWORD_1"))
        except ConnectionError as e:
            print("Wi-Fi failed:", e)
            show_message("Wi-Fi failed\nRetrying...")
            time.sleep(5)
    print("Wi-Fi connected, IP:", wifi.radio.ipv4_address)


# ---------- Main ----------
connect_wifi()
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

next_poll = 0
last_poll = 0
while True:
    t = now_ms()
    song_ended = (not track_group.hidden and is_playing
                  and duration_ms and position_ms() >= duration_ms)
    if t >= next_poll or (song_ended and t - last_poll > 1000):
        last_poll = t
        try:
            delay = poll()
        except (OSError, RuntimeError, ValueError) as e:
            print("Error:", e)
            delay = 10
            if not wifi.radio.connected:
                connect_wifi()
        gc.collect()
        next_poll = now_ms() + delay * 1000

    if not track_group.hidden:
        update_progress()
    time.sleep(0.2)
