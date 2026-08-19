# Spotify Now Playing
# Adafruit Feather ESP32-S3 + 3.5" TFT FeatherWing (HX8357, 480x320)
#
# Ported from spotify_api_micro.py (Jeff Trevino) for the separate-TFT setup.
# Further adapted by A Kleindolph with Claude

import os
import time

import board
import displayio
import socketpool
import ssl
import terminalio
import wifi

import adafruit_binascii
import adafruit_requests
from adafruit_display_text import bitmap_label
from fourwire import FourWire
import adafruit_hx8357

# ==================== CONFIGURATION ====================
# Everything lives in settings.toml at the top level of CIRCUITPY.
# No secrets.py, no my_spotify_creds.py.

ssid = os.getenv("WIFI_SSID_1")
password = os.getenv("WIFI_PASSWORD_1")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# Fail loudly here rather than with a confusing error much further down.
for _key, _value in (
    ("WIFI_SSID_1", ssid),
    ("WIFI_PASSWORD_1", password),
    ("SPOTIFY_CLIENT_ID", SPOTIFY_CLIENT_ID),
    ("SPOTIFY_CLIENT_SECRET", SPOTIFY_CLIENT_SECRET),
    ("SPOTIFY_REDIRECT_URI", SPOTIFY_REDIRECT_URI),
):
    if not _value:
        raise RuntimeError("settings.toml is missing " + _key)

# ==================== SETTINGS ====================

TOKEN_URL = "https://accounts.spotify.com/api/token"
CURRENT_TRACK_URL = "https://api.spotify.com/v1/me/player/currently-playing"
CACHED_TOKEN_PATH = "token.json"

POLL_SECONDS = 30  # dev-mode quota is shared per developer account - be polite
MAX_LINE = 25      # characters per line at scale 3 on a 480px-wide screen

# Build the Basic auth header once. Kept out of an f-string on purpose:
# nesting the same quote type inside an f-string is fragile in CircuitPython.
_credentials = SPOTIFY_CLIENT_ID + ":" + SPOTIFY_CLIENT_SECRET
_encoded = adafruit_binascii.b2a_base64(_credentials.encode())[:-1].decode("ascii")
AUTH_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization": "Basic " + _encoded,
}

# ==================== DISPLAY SETUP ====================
# The plain Feather ESP32-S3 has no built-in screen, so unlike the Reverse TFT
# there is no board.DISPLAY. We build the display object ourselves.

displayio.release_displays()  # must come first, or the 2nd run raises an error

spi = board.SPI()
display_bus = FourWire(
    spi,
    command=board.D10,      # DC  - hardwired on the FeatherWing
    chip_select=board.D9,   # CS  - hardwired on the FeatherWing
    reset=None,             # FeatherWing has no reset pin broken out
)
display = adafruit_hx8357.HX8357(display_bus, width=480, height=320)

# ==================== TEXT WRAPPING ====================


def wrap_text(text, max_line_length):
    """Break a string into lines no longer than max_line_length characters."""
    words = text.split()
    wrapped_lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= max_line_length:
            if current_line:
                current_line += " " + word
            else:
                current_line = word
        else:
            wrapped_lines.append(current_line)
            current_line = word
    if current_line:
        wrapped_lines.append(current_line)
    return "\n".join(wrapped_lines)


# ==================== DRAWING ====================


def draw(artist="", track="", album="", status="", status_color=0x888888):
    """Redraw the whole screen."""
    group = displayio.Group()

    artist_label = bitmap_label.Label(
        terminalio.FONT, text=wrap_text(artist, MAX_LINE), scale=3, color=0xFFFF00
    )
    artist_label.x = 10
    artist_label.y = 30
    group.append(artist_label)

    track_label = bitmap_label.Label(
        terminalio.FONT, text=wrap_text(track, MAX_LINE), scale=3, color=0x00FF00
    )
    track_label.x = 10
    track_label.y = artist_label.y + artist_label.bounding_box[3] * 3 + 20
    group.append(track_label)

    album_label = bitmap_label.Label(
        terminalio.FONT, text=wrap_text(album, MAX_LINE + 12), scale=2, color=0xAAAAAA
    )
    album_label.x = 10
    album_label.y = track_label.y + track_label.bounding_box[3] * 3 + 20
    group.append(album_label)

    # Status line pinned near the bottom so errors are visible without serial.
    status_label = bitmap_label.Label(
        terminalio.FONT, text=wrap_text(status, 39), scale=2, color=status_color
    )
    status_label.x = 10
    status_label.y = 295
    group.append(status_label)

    display.root_group = group


def show_status(message, color=0x888888):
    print(message)
    draw(status=message, status_color=color)


# ==================== INTERNET CONNECTION ====================

show_status("Connecting to " + ssid + "...")
wifi.radio.connect(ssid, password)
print("Connected. IP address:", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# ==================== AUTHORIZATION ====================


def post_to_token_endpoint(payload):
    """POST to Spotify's token endpoint and return the parsed JSON, or None."""
    response = None
    try:
        response = requests.post(TOKEN_URL, data=payload, headers=AUTH_HEADERS)
        data = response.json()
        if response.status_code != 200:
            print("Token request failed:", response.status_code, data)
            return None
        return data
    except Exception as error:
        print("Token request error:", error)
        return None
    finally:
        # Always close, or the board runs out of sockets and hangs.
        if response is not None:
            response.close()


def get_first_access_token_interactive():
    """Prompt for an authorization code and trade it for tokens."""
    show_status("Enter auth code in the serial console")
    authorization_code = input("Enter authorization code from redirect URL: ")
    return post_to_token_endpoint(
        {
            "grant_type": "authorization_code",
            "code": authorization_code.strip(),
            "redirect_uri": SPOTIFY_REDIRECT_URI,
        }
    )


def get_fresh_access_token():
    """Use the cached refresh token to get a new access token."""
    try:
        with open(CACHED_TOKEN_PATH, "r") as token_file:
            import json

            cached = json.load(token_file)
        refresh_token = cached["refresh_token"]
    except Exception as error:
        print("Could not read cached token:", error)
        return None

    print("Requesting a fresh access token using the cached refresh token...")
    return post_to_token_endpoint(
        {"grant_type": "refresh_token", "refresh_token": refresh_token}
    )


def cache_access_token(token_json):
    """Write the token JSON to the Feather's filesystem. Needs boot.py."""
    import json

    print("Caching token at", CACHED_TOKEN_PATH)
    try:
        with open(CACHED_TOKEN_PATH, "w") as cache_file:
            json.dump(token_json, cache_file)
    except OSError:
        print("Filesystem is read-only. Is boot.py present? Did you reset?")


def cached_token_exists():
    try:
        os.stat(CACHED_TOKEN_PATH)
        return True
    except OSError:
        return False


def delete_cached_token():
    try:
        os.remove(CACHED_TOKEN_PATH)
        print("Removed stale", CACHED_TOKEN_PATH)
    except OSError:
        pass


def ensure_access_token():
    """Return a valid token dict, refreshing or re-authorizing as needed."""
    token_json = None

    if cached_token_exists():
        token_json = get_fresh_access_token()
        if token_json is None:
            # Refresh token was rejected. Start over rather than loop forever.
            show_status("Refresh failed - re-authorizing", 0xFF8800)
            delete_cached_token()

    if token_json is None:
        token_json = get_first_access_token_interactive()

    if token_json is None:
        return None

    # A refresh response often omits refresh_token. Only overwrite the cache
    # when we actually received one, or we'd lose the ability to refresh.
    if "refresh_token" in token_json:
        cache_access_token(token_json)

    return token_json


# ==================== CURRENTLY PLAYING TRACK ====================


def get_currently_playing_track(access_token):
    """Return the response dict, or None. Prints a diagnosis on failure."""
    headers = {"Authorization": "Bearer " + access_token}
    response = None
    try:
        response = requests.get(CURRENT_TRACK_URL, headers=headers)
        code = response.status_code

        if code == 200:
            return response.json()

        if code == 204:
            show_status("Connected - nothing playing")
            return None

        if code == 401:
            print("401 Unauthorized - access token expired.")
            return None

        if code == 403:
            # The most likely failure under the 2026 dev-mode rules.
            # The body distinguishes the two causes, so print it verbatim.
            body = response.text
            print("403 Forbidden. Spotify said:", body)
            if "premium" in body.lower():
                show_status("403: app owner needs Premium", 0xFF0000)
            else:
                show_status("403: user not on app allowlist", 0xFF0000)
            return None

        if code == 429:
            retry_after = response.headers.get("retry-after", "?")
            print("429 rate limited/quota. Retry-After:", retry_after)
            print("Body:", response.text)
            show_status("429: slow down (retry " + str(retry_after) + "s)", 0xFF8800)
            return None

        print("Unexpected status code:", code, response.text)
        show_status("HTTP " + str(code), 0xFF0000)
        return None

    except Exception as error:
        print("Request error:", error)
        show_status("Network error", 0xFF0000)
        return None

    finally:
        if response is not None:
            response.close()


def extract_track(cp_json):
    """Pull artist / track / album out of the response, or None."""
    if not cp_json:
        return None
    item = cp_json.get("item")
    if not item:
        return None  # advertisement, podcast, or nothing loaded yet
    artists = ", ".join(artist["name"] for artist in item["artists"])
    album = item.get("album", {}).get("name", "")
    return (artists, item["name"], album)


# ==================== MAIN ====================

show_status("Authorizing with Spotify...")

token_json = None
token_expires_at = 0.0
last_seen = None

while True:
    # Refresh a minute early so a request never lands on an expired token.
    if token_json is None or time.monotonic() >= token_expires_at:
        token_json = ensure_access_token()
        if token_json is None:
            show_status("Could not get a token - check console", 0xFF0000)
            time.sleep(30)
            continue
        expires_in = token_json.get("expires_in", 3600)
        token_expires_at = time.monotonic() + expires_in - 60
        print("Got a token, valid for", expires_in, "seconds.")

    response = get_currently_playing_track(token_json["access_token"])

    if response is None:
        # 401 means the token died early; force a refresh next time around.
        token_expires_at = 0.0
        last_seen = None
        time.sleep(POLL_SECONDS)
        continue

    current = extract_track(response)

    if current is None:
        if last_seen is not None:
            show_status("Advertisement or podcast")
            last_seen = None
    elif current != last_seen:
        artist, track, album = current
        print("Now playing: {} - {}".format(artist, track))
        draw(artist=artist, track=track, album=album, status="")
        last_seen = current

    time.sleep(POLL_SECONDS)
