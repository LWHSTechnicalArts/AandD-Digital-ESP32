import os
import wifi

ssid = os.getenv("WIFI_SSID_1")
password = os.getenv("WIFI_PASSWORD_1")

print(f"Connecting to {ssid}")
wifi.radio.connect(ssid, password)
print(f"Connected! IP address: {wifi.radio.ipv4_address}")
