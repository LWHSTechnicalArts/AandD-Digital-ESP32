# Connect to whichever known WiFi network is available
# In settings.toml, list your networks in numbered pairs

import os
import wifi

MAX_NETWORKS = 3   # how many numbered pairs to look for in settings.toml

# --- The function -------------------------------------------------------
# A function is a named chunk of code that only runs when you call it.
# Writing it here doesn't do anything yet - it just defines the steps.
def connect_wifi():
    """Try each saved network in order. Stops at the first one that works."""
    for number in range(1, MAX_NETWORKS + 1):
        
        # Build the key names to look up: WIFI_SSID_1, WIFI_SSID_2, ...
        ssid = os.getenv("WIFI_SSID_" + str(number))
        password = os.getenv("WIFI_PASSWORD_" + str(number))
        
        # os.getenv gives back None when that key isn't in settings.toml,
        # so skip any numbers you haven't filled in.
        if ssid is None:
            continue

        print("Trying", ssid, "...")
        try:
            # timeout keeps us from waiting forever on a network that isn't here
            wifi.radio.connect(ssid, password, timeout=10)
            print("Connected to", ssid)
            print("IP address:", wifi.radio.ipv4_address)
            return True          # success - leave the function right now

        except ConnectionError:
            # Wrong password, or the network isn't in range. Try the next one.
            print("No luck with", ssid)

    print("Could not connect to any saved network.")
    return False

# This line is where the function actually runs. It happens one time,
# before the main loop, because you only need to connect once.
connect_wifi()

# --- Your program goes here ---------------------------------------------
while True:
    pass
