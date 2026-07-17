import array
import math
import board
import audiobusio
import time

mic = audiobusio.PDMIn(board.A0, board.A1, sample_rate=16000, bit_depth=16)
samples = array.array("H", [0] * 320)

REFERENCE = 32768
DB_OFFSET = 100

# Initialize smoothing history
SMOOTHING = 5
db_history = [40] * SMOOTHING

def mean(values):
    return sum(values) / len(values)

def normalized_rms(values):
    minbuf = int(mean(values))
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )
    return math.sqrt(samples_sum / len(values))

while True:
    mic.record(samples, len(samples))
    rms = normalized_rms(samples)

    if rms == 0:
        rms = 0.0001

    db = 20 * (math.log(rms / REFERENCE) / math.log(10)) + DB_OFFSET
    db = max(db, 30)

    # Smooth the reading
    db_history.append(db)
    db_history.pop(0)
    smoothed_db = sum(db_history) / SMOOTHING

    print(f"dB: {smoothed_db:.1f}")
    time.sleep(0.1)
