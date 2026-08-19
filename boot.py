import board
import digitalio
import storage

# Hold the BOOT button while resetting to keep CIRCUITPY editable
# from your laptop. Otherwise the Feather can write token.json.
try:
    button = digitalio.DigitalInOut(board.BOOT0)
    button.switch_to_input(pull=digitalio.Pull.UP)
    laptop_wins = not button.value  # button pressed pulls the pin low
    button.deinit()
except AttributeError:
    laptop_wins = False
