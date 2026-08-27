# SPDX-License-Identifier: Unlicense
# Created and Verified: A Kleindolph, August 2026 — tested on Feather ESP32-S3 with Circuitpy v10

import time  # gives us access to time.sleep() for delays

while True:  # loop forever - this keeps running until the board is reset or code changes
    print("Hello, CircuitPython!")  # send this text to the serial console
    time.sleep(1)  # pause for 1 second before looping again
