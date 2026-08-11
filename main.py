import serial


class FootPressureSensor:
    def __init__(self, name, port, baud_rate=115200):
        self.name = name
        self.serial = serial.Serial(port, baud_rate, timeout=1)
        self.pressures = [0] * 48

    def read_packet(self):
        while True:
            if self.serial.read(1) != b"\x40":
                continue

            packet = b"\x40" + self.serial.read(98)

            if len(packet) != 99:
                continue

            calculated_checksum = sum(packet[:98]) & 0xFF
            received_checksum = packet[98]

            if calculated_checksum != received_checksum:
                print(f"{self.name}: bad checksum")
                continue

            return packet

    def update(self):
        packet = self.read_packet()

        for i in range(48):
            high = packet[2 + i * 2]
            low = packet[3 + i * 2]
            self.pressures[i] = (high << 8) | low

    def print_pressures(self):
        print(f"{self.name:5} | ", end="")

        for i, value in enumerate(self.pressures):
            print(f"{i + 1:02}:{value:05}", end="  ")

        print()


left = FootPressureSensor("Left", "COM7")
right = FootPressureSensor("Right", "COM8")


while True:
    left.update()
    right.update()

    left.print_pressures()
    right.print_pressures()