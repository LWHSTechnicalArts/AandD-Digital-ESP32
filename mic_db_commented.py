# ============================================================
# Sound Level Meter - Feather ESP32-S3 + PDM Microphone
# ============================================================
# This program reads audio from a microphone and prints the
# sound level in decibels (dB) to the serial monitor.
# Decibels are how we measure loudness -- the higher the number,
# the louder the sound. Normal conversation is about 60 dB.

# --- Wiring ---
# CLK → A0  (clock signal -- keeps the mic and board in sync)
# DAT → A1  (data signal -- carries the actual audio)
# 3V  → 3.3V
# GND → GND

# --- Libraries ---
# These are pre-written tools we import to help us do specific jobs
import array       # lets us create a fast, fixed-size list of numbers
import math        # gives us math functions like log() and sqrt()
import board       # lets us refer to pins by name (A0, A1, etc.)
import audiobusio  # handles communication with the PDM microphone
import time        # lets us pause the program with time.sleep()

# --- Set Up the Microphone ---
# Tell CircuitPython where the mic is wired and how to talk to it.
# sample_rate=16000 means we take 16,000 audio snapshots per second.
# bit_depth=16 means each snapshot is stored as a 16-bit number (0-65535).
mic = audiobusio.PDMIn(board.A0, board.A1, sample_rate=16000, bit_depth=16)

# Create a list to store 320 audio samples at a time.
# "H" means each value is an unsigned 16-bit integer (0 to 65535).
samples = array.array("H", [0] * 320)

# --- Calibration Settings ---
# REFERENCE is the maximum possible sample value for 16-bit audio.
# We use it to calculate how loud the sound is relative to the max.
REFERENCE = 32768

# DB_OFFSET shifts our dB reading up or down to match real-world levels.
# Increase this number if readings seem too low, decrease if too high.
DB_OFFSET = 100

# --- Smoothing Settings ---
# Microphone readings can jump around a lot from moment to moment.
# To smooth things out, we keep a short history of recent readings
# and average them together before displaying.
SMOOTHING = 5  # number of recent readings to average

# Pre-fill the history list with a reasonable starting value (40 dB).
# This prevents weird low readings right when the program starts.
db_history = [40] * SMOOTHING


# --- Helper Functions ---

# Calculates the average (mean) of a list of numbers.
def mean(values):
    return sum(values) / len(values)

# Calculates the "normalized RMS" of the audio samples.
# RMS (Root Mean Square) is a way of measuring the overall energy
# in a signal -- louder sounds produce higher RMS values.
# We "normalize" by first removing the DC bias (the average value),
# so that silence reads close to zero instead of a middle value.
def normalized_rms(values):
    # Find the average sample value (the DC bias / background offset)
    minbuf = int(mean(values))

    # Subtract the bias from each sample, square it, and sum them all up.
    # Squaring makes all values positive and emphasizes louder sounds.
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )

    # Return the square root of the average -- that's the RMS value.
    return math.sqrt(samples_sum / len(values))


# --- Main Loop ---
# This loop runs forever, continuously reading and printing the sound level.
while True:

    # Fill the samples list with fresh audio data from the microphone.
    mic.record(samples, len(samples))

    # Calculate the RMS (loudness) of those samples.
    rms = normalized_rms(samples)

    # Avoid a math error -- log(0) is undefined, so set a tiny minimum.
    if rms == 0:
        rms = 0.0001

    # Convert RMS to decibels using the standard dB formula:
    # dB = 20 * log10(signal / reference)
    # CircuitPython doesn't have log10, so we use log(x)/log(10) instead.
    # DB_OFFSET shifts the result into a realistic dB range.
    db = 20 * (math.log(rms / REFERENCE) / math.log(10)) + DB_OFFSET

    # Clamp the minimum to 30 dB so we don't display unrealistic
    # negative numbers during silence.
    db = max(db, 30)

    # Add the new reading to our history and remove the oldest one.
    # This keeps the list at a fixed length of SMOOTHING values.
    db_history.append(db)
    db_history.pop(0)

    # Average the history list to get a smooth, stable reading.
    smoothed_db = sum(db_history) / SMOOTHING

    # Print the result to the serial monitor, rounded to 1 decimal place.
    print(f"dB: {smoothed_db:.1f}")

    # Wait 0.1 seconds before taking the next reading (10 times per second).
    time.sleep(0.1)
