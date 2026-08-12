# SHT4x temperature + humidity on Feather ESP32-S3 (CircuitPython)
# Needs in /lib: adafruit_sht4x.mpy, adafruit_bus_device/

import time
import board
import adafruit_sht4x

# STEMMA QT connector -- use board.I2C() if wired to the SCL/SDA pads
i2c = board.STEMMA_I2C()
sht = adafruit_sht4x.SHT4x(i2c)

print("Serial number:", hex(sht.serial_number))

# No heater, best accuracy -- the normal choice
sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION

while True:
    # returns (temp in C, relative humidity in %)
    temperature, relative_humidity = sht.measurements
    print(f"Temp: {temperature:.1f} °C   Humidity: {relative_humidity:.1f} %")
    time.sleep(1)  # avoid self-heating from constant polling
