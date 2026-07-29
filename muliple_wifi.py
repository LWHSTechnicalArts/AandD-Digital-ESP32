import os
import wifi
 
MAX_NETWORKS = 3
 
def connect_wifi():
    for number in range(1, MAX_NETWORKS + 1):
        ssid = os.getenv("WIFI_SSID_" + str(number))
        password = os.getenv("WIFI_PASSWORD_" + str(number))
        if ssid is None:
            continue
        print("Trying", ssid, "...")
        try:
            wifi.radio.connect(ssid, password, timeout=10)
            print("Connected to", ssid)
            print("IP address:", wifi.radio.ipv4_address)
            return True
        except ConnectionError:
            print("No luck with", ssid)
    print("Could not connect to any saved network.")
    return False
 
connect_wifi()
 
while True:
    pass #your code here
 
