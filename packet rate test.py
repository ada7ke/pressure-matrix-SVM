import serial, time

PORT = "COM7"

s = serial.Serial(PORT, 115200, timeout=0.1)

total_bytes = 0
last_total = 0
last_time = time.time()

while True:
    data = s.read(s.in_waiting or 1)
    total_bytes += len(data)

    now = time.time()

    if now - last_time >= 1:
        bytes_per_second = total_bytes - last_total

        print(
            f"bytes/s: {bytes_per_second:5} | "
            f"in_waiting: {s.in_waiting:3}"
        )

        last_total = total_bytes
        last_time = now