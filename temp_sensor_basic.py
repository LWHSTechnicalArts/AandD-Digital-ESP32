import time
import board
import adafruit_sht4x

i2c = board.STEMMA_I2C()   # use board.I2C() if you wired to SCL/SDA instead
sht = adafruit_sht4x.SHT4x(i2c)

print("Serial number:", hex(sht.serial_number))
sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
print("Mode:", adafruit_sht4x.Mode.string[sht.mode])

while True:
    temperature, relative_humidity = sht.measurements
    print(f"Temp: {temperature:.1f} °C   Humidity: {relative_humidity:.1f} %")
    time.sleep(1)
