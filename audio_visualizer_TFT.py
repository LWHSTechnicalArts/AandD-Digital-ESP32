"""
SPDX-License-Identifier: Unlicense

AI-assisted: "Claude (Anthropic)", September 2026
Human contribution: idea / circuit design / pin mapping / debugging / testing on hardware
Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with CircuitPython v10

CircuitPython rolling level visualizer -- smooth line

Hardware:
  - Adafruit Feather ESP32-S3
  - Adafruit PDM Microphone Breakout   CLK -> A0, DAT -> A1, 3V, GND
  - 3.5" 480x320 TFT, HX8357 driver    CS -> D9, DC -> D10, no reset
"""

import math
import random
import time
import board
import busio
import audiobusio
import displayio
import fourwire
import bitmaptools
import adafruit_hx8357
from array import array

CALIBRATE = False
DEBUG = True

# -----------------------------
# Look
# -----------------------------
TRACE_STYLE = "mirror"     # "mirror", "single", "filled"
RANDOM_COLOR_PER_SWEEP = True   # new colour each time the sweep wraps
LINE_WIDTH = 3             # pixels. Costs almost nothing: it adds a few rows
                           # to the refreshed rectangle, and that rectangle is
                           # only about six columns wide. 4 or 5 is fine too.

# Out of 256. Attack is how fast the line climbs, release how slowly it falls.
# Raise RELEASE for a livelier trace, lower it for a lazier one.
ATTACK = 170
RELEASE = 22

# -----------------------------
# Levels
# -----------------------------
AUTO_GATE = True
DEFAULT_NOISE_GATE = 80
FULL_SCALE = 5000          # RMS runs lower than peak, so this is below the
                           # value the filled version wanted
SCALE_MODE = "log"

GATE_MIN = 30
GATE_MAX = 1500

NOISE_GATE = DEFAULT_NOISE_GATE

# -----------------------------
# Display
# -----------------------------
WIDTH = 480
HEIGHT = 320
CENTER_Y = HEIGHT // 2
MAX_AMPLITUDE = CENTER_Y - 4

SPI_BAUDRATE = 24000000

displayio.release_displays()

spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)
display_bus = fourwire.FourWire(
    spi,
    command=board.D10,
    chip_select=board.D9,
    reset=None,
    baudrate=SPI_BAUDRATE,
)

display = adafruit_hx8357.HX8357(display_bus, width=WIDTH, height=HEIGHT)
display.auto_refresh = False

BLACK_IDX = 0
CENTER_IDX = 1
CLIP_IDX = 2
FIRST_TRACE_IDX = 3

# Preloaded, never modified at runtime. Recoloring a palette entry would
# repaint every pixel already using it and force a full-screen refresh; simply
# drawing with a different index costs nothing.
TRACE_COLORS = (
    0x00FF00,  # green
    0x00E5FF,  # cyan
    0xFF00E0,  # magenta
    0xFFD400,  # amber
    0xFF6A00,  # orange
    0x7CFF00,  # lime
    0x00A2FF,  # azure
    0xFF3B7B,  # rose
    0xB14CFF,  # violet
    0x00FFB0,  # mint
    0xFFFFFF,  # white
    0x9BFF6A,  # pale green
    0xFF9E4C,  # peach
)
print ("hello")
# Sixteen entries means 4 bits per pixel instead of 2, so the bitmap is 77 KB
# rather than 38 KB. The bytes sent over SPI are unchanged -- displayio
# converts to RGB565 on the way out regardless of the source depth.
PALETTE_SIZE = 16

palette = displayio.Palette(PALETTE_SIZE)
for _slot in range(PALETTE_SIZE):
    palette[_slot] = 0x000000
palette[CENTER_IDX] = 0x404040
palette[CLIP_IDX] = 0xFF3030
for _offset, _color in enumerate(TRACE_COLORS):
    palette[FIRST_TRACE_IDX + _offset] = _color

background = displayio.Bitmap(WIDTH, HEIGHT, PALETTE_SIZE)
background.fill(BLACK_IDX)

group = displayio.Group()
group.append(displayio.TileGrid(background, pixel_shader=palette))
display.root_group = group

# -----------------------------
# Microphone
# -----------------------------
mic = audiobusio.PDMIn(board.A0, board.A1, sample_rate=16000, bit_depth=16)

BLOCK = 32
raw = array("H", [0] * BLOCK)
GAP = 4

DC_SMOOTHING = 64
dc_offset = 0


def read_level():
    """Record one block. Returns (rms, mean) as signed values.

    One pass gives both: variance is the mean of the squares minus the square
    of the mean, so the DC estimate falls out of the same loop as the RMS.
    """
    mic.record(raw, BLOCK)
    total = 0
    total_squares = 0
    for i in range(BLOCK):
        value = raw[i]
        if value >= 32768:
            value -= 65536
        total += value
        total_squares += value * value
    mean = total // BLOCK
    variance = total_squares // BLOCK - mean * mean
    if variance < 1:
        return 0, mean
    return int(math.sqrt(variance)), mean


def track_dc(block_mean):
    """Trim slow drift. Only corrects past the smoothing step, because floor
    division on a small negative error would walk the offset down forever."""
    global dc_offset
    dc_error = block_mean - dc_offset
    if dc_error > DC_SMOOTHING or dc_error < -DC_SMOOTHING:
        dc_offset += dc_error // DC_SMOOTHING


# -----------------------------
# Level -> pixel height table
# -----------------------------
LUT_SHIFT = 4
LUT_SIZE = (32768 >> LUT_SHIFT) + 1
height_lut = array("h", [0] * LUT_SIZE)


def build_height_table():
    span = FULL_SCALE - NOISE_GATE
    if span < 1:
        span = 1
    log10 = math.log(10)
    for i in range(LUT_SIZE):
        magnitude = i << LUT_SHIFT
        if magnitude <= NOISE_GATE:
            height = 0
        else:
            ratio = (magnitude - NOISE_GATE) / span
            if ratio > 1.0:
                ratio = 1.0
            if SCALE_MODE == "log":
                height = int(MAX_AMPLITUDE * math.log(1 + 9 * ratio) / log10)
            else:
                height = int(MAX_AMPLITUDE * ratio)
        if height > MAX_AMPLITUDE:
            height = MAX_AMPLITUDE
        height_lut[i] = height


def scaled(level):
    if level < 0:
        level = 0
    elif level > 32767:
        level = 32767
    return height_lut[level >> LUT_SHIFT]


# -----------------------------
# Drawing
# -----------------------------
def draw_guide_span(x0, x1):
    x = x0 + ((-x0) % 4)
    while x < x1:
        background[x, CENTER_Y] = CENTER_IDX
        x += 4


def erase_span(x0, x1):
    if x1 <= x0:
        return
    bitmaptools.fill_region(background, x0, 0, x1, HEIGHT, BLACK_IDX)
    draw_guide_span(x0, x1)


def draw_segment(x, y_from, y_to, color):
    """Fill one column from the previous column's value to this one's, plus
    the line thickness.

    One C call per column instead of LINE_WIDTH stacked draw_line calls, so
    thickness costs nothing. Because each column spans the gap to its
    neighbour, the trace stays connected however steeply it moves, and a
    vertical run comes out as thick as a horizontal one -- which stacked
    lines could not manage.
    """
    if y_to < y_from:
        y_from, y_to = y_to, y_from
    y_from -= LINE_WIDTH // 2
    y_to += LINE_WIDTH - LINE_WIDTH // 2
    if y_from < 0:
        y_from = 0
    if y_to > HEIGHT:
        y_to = HEIGHT
    if y_to <= y_from:
        return
    bitmaptools.fill_region(background, x, y_from, x + 1, y_to, color)


def collect_levels(duration, limit=400):
    levels = []
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        rms, block_mean = read_level()
        track_dc(block_mean)
        levels.append(rms)
        if len(levels) >= limit:
            break
    levels.sort()
    return levels


# Settle the DC estimate before measuring anything.
for _ in range(8):
    _, first_mean = read_level()
    dc_offset = (dc_offset * 7 + first_mean) // 8

# -----------------------------
# Calibration mode
# -----------------------------
if CALIBRATE:
    print("Stay quiet for one second while the noise floor is measured.")
    quiet = collect_levels(1.0)
    floor = quiet[(len(quiet) * 9) // 10]
    print("Floor RMS around {}. Suggested NOISE_GATE: {}".format(
        floor, int(floor * 1.5) + 10
    ))
    print("")
    print("Now make your loudest expected sound. Ctrl-C when done.")
    session_peak = 0
    window_peak = 0
    last_print = time.monotonic()
    while True:
        rms, block_mean = read_level()
        track_dc(block_mean)
        if rms > window_peak:
            window_peak = rms
        if rms > session_peak:
            session_peak = rms
        now = time.monotonic()
        if now - last_print >= 1.0:
            print("rms now {:6d}   suggested FULL_SCALE: {:6d}".format(
                window_peak, session_peak
            ))
            window_peak = 0
            last_print = now

# -----------------------------
# Automatic noise gate
# -----------------------------
if AUTO_GATE:
    measured = collect_levels(1.0)
    floor = measured[(len(measured) * 9) // 10]
    NOISE_GATE = int(floor * 1.5) + 10
    if NOISE_GATE < GATE_MIN:
        NOISE_GATE = GATE_MIN
    elif NOISE_GATE > GATE_MAX:
        NOISE_GATE = GATE_MAX
    if DEBUG:
        print("Measured floor {}, noise gate set to {}".format(floor, NOISE_GATE))

build_height_table()

if DEBUG:
    print("Gate {}  full scale {}  style {}".format(
        NOISE_GATE, FULL_SCALE, TRACE_STYLE
    ))

background.fill(BLACK_IDX)
draw_guide_span(0, WIDTH)
display.refresh()

cursor = 0
smoothed = 0
previous_y = None
trace_idx = FIRST_TRACE_IDX
frame_count = 0
window_peak = 0
clip_count = 0
last_report = time.monotonic()

# -----------------------------
# Main loop
# -----------------------------
while True:
    rms, block_mean = read_level()
    track_dc(block_mean)

    # Fast attack, slow release. Written as two branches so the integer
    # division always operates on a positive number -- floor division on a
    # negative delta rounds away from zero and biases the decay.
    delta = rms - smoothed
    if delta > 0:
        smoothed += (delta * ATTACK) // 256
    else:
        smoothed -= ((-delta) * RELEASE) // 256

    offset = scaled(smoothed)

    if offset >= MAX_AMPLITUDE:
        color = CLIP_IDX
        clip_count += 1
    else:
        color = trace_idx

    y = CENTER_Y - offset

    gap_start = cursor + 1
    if gap_start + GAP <= WIDTH:
        erase_span(gap_start, gap_start + GAP)
    else:
        erase_span(gap_start, WIDTH)
        erase_span(0, (gap_start + GAP) - WIDTH)

    if TRACE_STYLE == "filled":
        bitmaptools.fill_region(
            background, cursor, y, cursor + 1, HEIGHT - y, color
        )
    else:
        # After a wrap there is no previous column to reach back to, so the
        # segment is just this column's own value.
        start_y = y if previous_y is None else previous_y
        draw_segment(cursor, start_y, y, color)
        if TRACE_STYLE == "mirror":
            draw_segment(
                cursor,
                CENTER_Y + (CENTER_Y - start_y),
                CENTER_Y + offset,
                color,
            )

    display.refresh()

    previous_y = y
    cursor += 1
    if cursor >= WIDTH:
        cursor = 0
        # Do not join the right edge back to the left, or the trace streaks
        # across the whole screen once per sweep.
        previous_y = None
        if RANDOM_COLOR_PER_SWEEP and len(TRACE_COLORS) > 1:
            # Only the sweep being drawn and the one being erased ahead of it
            # are ever on screen together, so avoiding an immediate repeat is
            # enough to keep every index unambiguous.
            new_idx = trace_idx
            while new_idx == trace_idx:
                new_idx = FIRST_TRACE_IDX + random.randrange(len(TRACE_COLORS))
            trace_idx = new_idx

    frame_count += 1
    if DEBUG:
        if rms > window_peak:
            window_peak = rms
        now = time.monotonic()
        if now - last_report >= 1.0:
            print("cols/s {:4d}  dc {:6d}  rms {:6d}  smoothed {:6d}  clipped {:4d}".format(
                frame_count, dc_offset, window_peak, smoothed, clip_count
            ))
            frame_count = 0
            window_peak = 0
            clip_count = 0
            last_report = now=
