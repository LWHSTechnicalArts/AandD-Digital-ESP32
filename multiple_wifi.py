# Connect to whichever known WiFi network is available
#
# In settings.toml, list your networks in numbered pairs:
#   WIFI_SSID_1 = "HomeNetwork"
#   WIFI_PASSWORD_1 = "firstpassword"
#   WIFI_SSID_2 = "SchoolWiFi"
#   WIFI_PASSWORD_2 = "secondpassword"

import os
import wifi

# --- Read the networks out of settings.toml -----------------------------
# Count upward - WIFI_SSID_1, WIFI_SSID_2, and so on - until we ask for a
# number that isn't there. os.getenv gives back None when a key is missing,
# and that's our signal to stop looking.
networks = []
number = 1
while True:
    ssid = os.getenv("WIFI_SSID_" + str(number))
    password = os.getenv("WIFI_PASSWORD_" + str(number))
    if ssid is None:
        break
    networks.append((ssid, password))
    number = number + 1

print("Found", len(networks), "saved networks")

# --- Try each one until something works ---------------------------------
connected = False

for ssid, password in networks:
    print("Trying", ssid, "...")
    try:
        # timeout keeps us from waiting forever on a network that isn't here
        wifi.radio.connect(ssid, password, timeout=10)
        print("Connected to", ssid)
        print("IP address:", wifi.radio.ipv4_address)
        connected = True
        break          # stop as soon as one succeeds
    except ConnectionError:
        # Wrong password, or the network isn't in range. Move on.
        print("No luck with", ssid)

if not connected:
    print("Could not connect to any saved network.")
