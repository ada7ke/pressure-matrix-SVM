import serial, time

PORT = "COM8"

s = serial.Serial(PORT, 115200, timeout=0.1)

packet_count = 0
last_print = time.time()

while True:
    data = s.read(s.in_waiting or 1)

    if data:
        packet_count += len(data)

    if time.time() - last_print >= 1:
        print(
            f"bytes received this second: {packet_count}, "
            f"currently buffered: {s.in_waiting}"
        )

        packet_count = 0
        last_print = time.time()