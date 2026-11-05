# Muni arrivals on the 3.5" TFT FeatherWing — CircuitPython 10 — fancy edition
# /lib needs: adafruit_display_text, adafruit_display_shapes, adafruit_hx8357,
#             adafruit_connection_manager, adafruit_requests
# Made in collaboration with Claude

import os
import time

import bitmaptools
import board
import displayio
import fourwire
import terminalio
import vectorio
import wifi
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_text import label

import adafruit_connection_manager
import adafruit_hx8357
import adafruit_requests

STOP_CODE = "13548"
URL = (
    "https://webservices.umoiq.com/api/pub/v1/agencies/sfmta-cis"
    f"/stopcodes/{STOP_CODE}/predictions?key={os.getenv('UMOIQ_API_KEY')}"
)
REFRESH = 30          # seconds between fetches
TICK = 0.5            # animation step
HORIZON = 20          # minutes that map onto the full progress bar
W, H = 480, 320
FONT = terminalio.FONT

# ---- palette ---------------------------------------------------------------
BG_TOP, BG_BOTTOM = (0x0B, 0x10, 0x24), (0x22, 0x0E, 0x30)
CARD, CARD_EDGE = 0x141A36, 0x2C3358
MUNI_RED = 0xBF2B45
INK, DIM = 0xF4F1EA, 0x8A93A6
CYAN, AMBER, HOT = 0x3DE0FF, 0xFFB020, 0xFF4D5E
LIVE, LIVE_DIM, DEAD = 0x3DDC84, 0x1E6E42, 0xFF4D5E
TRACK = 0x252B48
GHOST = 0x1D2445      # unlit segments, like a real LED sign


def urgency_color(m):
    if m <= 1:
        return HOT
    if m <= 5:
        return AMBER
    return CYAN


def fit(s, n):
    return s if len(s) <= n else s[: n - 2] + ".."


def text(t, scale, color, anchor, pos):
    lbl = label.Label(FONT, text=t, color=color, scale=scale)
    lbl.anchor_point = anchor
    lbl.anchored_position = pos
    return lbl


# ---- display ---------------------------------------------------------------
displayio.release_displays()
display = adafruit_hx8357.HX8357(
    fourwire.FourWire(board.SPI(), command=board.D10, chip_select=board.D9),
    width=W,
    height=H,
)
display.auto_refresh = False  # redraw once per tick, no tearing

root = displayio.Group()

# Vertical gradient: a tiny 30x20 bitmap scaled 16x fills the screen cheaply.
rows = H // 16
grad_pal = displayio.Palette(rows)
grad_bmp = displayio.Bitmap(W // 16, rows, rows)
for y in range(rows):
    t = y / (rows - 1)
    r, g, b = (int(BG_TOP[k] + (BG_BOTTOM[k] - BG_TOP[k]) * t) for k in range(3))
    grad_pal[y] = (r << 16) | (g << 8) | b
    bitmaptools.fill_region(grad_bmp, 0, y, W // 16, y + 1, y)
bg = displayio.Group(scale=16)
bg.append(displayio.TileGrid(grad_bmp, pixel_shader=grad_pal))
root.append(bg)

# Header: route badge + route title + stop name
root.append(RoundRect(8, 8, 464, 66, 14, fill=CARD, outline=CARD_EDGE))
root.append(RoundRect(16, 16, 76, 50, 12, fill=MUNI_RED))
badge = text("--", 3, INK, (0.5, 0.5), (54, 41))
route_title = text("Muni", 2, INK, (0, 0.5), (106, 30))
stop_name = text(f"stop {STOP_CODE}", 2, DIM, (0, 0.5), (106, 54))
root.append(badge)
root.append(route_title)
root.append(stop_name)

# Hero card: next arrival
root.append(RoundRect(8, 84, 300, 178, 18, fill=CARD, outline=CARD_EDGE))
root.append(text("N E X T", 2, DIM, (0, 0), (24, 96)))

# --- seven-segment digits drawn with vectorio (crisp at any size) ---
#   aaa
#  f   b
#   ggg
#  e   c
#   ddd
SEGMENTS = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg",
    "-": "g", " ": "",
}


class SevenSeg(displayio.Group):
    """Right-aligned row of seven-segment digits made of hexagon polygons."""

    def __init__(self, x, y, digits=2, width=56, height=108, thick=12, gap=12):
        super().__init__()
        self._lit_pal = displayio.Palette(1)
        self._lit_pal[0] = INK
        ghost_pal = displayio.Palette(1)
        ghost_pal[0] = GHOST
        self._digits = []
        for i in range(digits):
            ox = x + i * (width + gap)
            # ghosts first so the lit segments draw on top
            self._segments(ox, y, width, height, thick, ghost_pal)
            self._digits.append(self._segments(ox, y, width, height, thick, self._lit_pal))

    def _segments(self, ox, oy, w, h, thick, pal):
        t = thick // 2
        g = 2  # hairline gap between segments
        left, right = ox + t, ox + w - t
        top, mid, bottom = oy + t, oy + h // 2, oy + h - t
        hl = right - left - 2 * g          # horizontal segment length
        vl = mid - top - 2 * g             # vertical segment length
        hpts = [(0, 0), (t, -t), (hl - t, -t), (hl, 0), (hl - t, t), (t, t)]
        vpts = [(0, 0), (t, t), (t, vl - t), (0, vl), (-t, vl - t), (-t, t)]
        spots = {
            "a": (hpts, left + g, top), "g": (hpts, left + g, mid),
            "d": (hpts, left + g, bottom),
            "f": (vpts, left, top + g), "b": (vpts, right, top + g),
            "e": (vpts, left, mid + g), "c": (vpts, right, mid + g),
        }
        segs = {}
        for name, (pts, sx, sy) in spots.items():
            poly = vectorio.Polygon(pixel_shader=pal, points=pts, x=sx, y=sy)
            segs[name] = poly
            self.append(poly)
        return segs

    def show(self, s):
        s = s[-len(self._digits):]
        s = " " * (len(self._digits) - len(s)) + s  # right-align
        for segs, ch in zip(self._digits, s):
            on = SEGMENTS.get(ch, "")
            for name, poly in segs.items():
                poly.hidden = name not in on

    @property
    def color(self):
        return self._lit_pal[0]

    @color.setter
    def color(self, value):
        self._lit_pal[0] = value  # recolors every lit segment at once


big = SevenSeg(76, 124)
big.show("--")
big_unit = text("min", 3, DIM, (0, 1), (214, 232))
root.append(big)
root.append(big_unit)

# Progress bar: fills up as the bus gets closer
BAR_X, BAR_Y, BAR_W, BAR_H = 24, 240, 268, 8
bar_pal = displayio.Palette(2)
bar_pal[0], bar_pal[1] = TRACK, CYAN
bar_bmp = displayio.Bitmap(BAR_W, BAR_H, 2)
root.append(displayio.TileGrid(bar_bmp, pixel_shader=bar_pal, x=BAR_X, y=BAR_Y))

# Right column: the following arrivals
root.append(text("T H E N", 2, DIM, (0, 0), (324, 96)))
later = []
for i, y in enumerate((122, 196)):
    root.append(RoundRect(320, y, 152, 64, 14, fill=CARD, outline=CARD_EDGE))
    lbl = text("--", 3, DIM, (0.5, 0.5), (396, y + 32))
    later.append(lbl)
    root.append(lbl)

# Footer: live dot, status, countdown
dot = Circle(22, 291, 7, fill=LIVE_DIM)
status = text("connecting", 2, DIM, (0, 0.5), (38, 291))
countdown = text("", 2, DIM, (1, 0.5), (472, 291))
root.append(dot)
root.append(status)
root.append(countdown)

display.root_group = root
display.refresh()


# ---- rendering -------------------------------------------------------------
def set_bar(fraction, color):
    bar_pal[1] = color
    filled = int(BAR_W * max(0.0, min(1.0, fraction)))
    bitmaptools.fill_region(bar_bmp, 0, 0, BAR_W, BAR_H, 0)
    if filled:
        bitmaptools.fill_region(bar_bmp, 0, 0, filled, BAR_H, 1)


def render(bus, minutes):
    route = bus["route"]
    title = route.get("title", "")
    badge.text = fit(route.get("id") or title.split("-")[0], 3)
    route_title.text = fit(title, 30)
    stop_name.text = fit(bus["stop"]["name"], 30)

    if not minutes:
        big.show("--")
        big.color = DIM
        big_unit.hidden = True
        set_bar(0, TRACK)
        status.text = "no buses right now"
    else:
        m = minutes[0]
        big.show(str(min(m, 99)))
        big.color = urgency_color(m)
        big_unit.hidden = False
        big_unit.text = "NOW" if m == 0 else "min"
        big_unit.color = HOT if m == 0 else DIM
        set_bar(1 - m / HORIZON, big.color)
        status.text = f"live  stop {STOP_CODE}"

    for i, lbl in enumerate(later):
        if i + 1 < len(minutes):
            lbl.text, lbl.color = f"{minutes[i + 1]} min", INK
        else:
            lbl.text, lbl.color = "--", DIM


# ---- network ---------------------------------------------------------------
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)


def fetch():
    if not wifi.radio.connected:
        wifi.radio.connect(os.getenv("WIFI_SSID_1"), os.getenv("WIFI_PASSWORD_1"))
    with requests.get(URL) as response:
        bus = response.json()[0]  # .json() once — each call is a fetch
    return bus, sorted(v["minutes"] for v in bus["values"])


# ---- main loop -------------------------------------------------------------
online = False
pulsing = False   # next bus is <= 1 min away
last_fetch = -REFRESH
tick = 0

while True:
    now = time.monotonic()
    if now - last_fetch >= REFRESH:
        last_fetch = now
        countdown.text = "updating..."
        display.refresh()
        try:
            bus, minutes = fetch()
            render(bus, minutes)
            online = True
            pulsing = bool(minutes) and minutes[0] <= 1
            print(bus["route"]["title"], minutes)
        except Exception as err:
            print("failed:", err)
            online, pulsing = False, False
            big.color = DIM
            status.text = "offline - retrying"

    # animations
    tick += 1
    blink = tick % 2 == 0
    if online:
        dot.fill = LIVE if blink else LIVE_DIM
    else:
        dot.fill = DEAD
    if pulsing:
        big.color = HOT if blink else INK

    countdown.text = f"next {max(0, int(REFRESH - (time.monotonic() - last_fetch)))}s"
    display.refresh()
    time.sleep(TICK)
