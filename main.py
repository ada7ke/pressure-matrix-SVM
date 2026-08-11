import serial
import tkinter as tk


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


class FootGrid:
    def __init__(self, parent, name, sensor, sensor_numbers):
        self.sensor = sensor
        self.sensor_numbers = sensor_numbers
        self.cells = {}

        frame = tk.LabelFrame(parent, text=name, font=("Arial", 16, "bold"), padx=10, pady=10)
        frame.pack(side=tk.LEFT, padx=20, pady=20)

        for row in range(12):
            for col in range(4):
                sensor_number = sensor_numbers[row][col]

                cell = tk.Label(
                    frame,
                    text=f"{sensor_number}\n0",
                    width=7,
                    height=3,
                    font=("Arial", 11, "bold"),
                    relief="solid",
                    borderwidth=1,
                    bg="white"
                )

                cell.grid(row=row, column=col, padx=2, pady=2)
                self.cells[sensor_number] = cell

    def pressure_to_color(self, pressure):
        max_pressure = 100

        pressure = max(0, min(pressure, max_pressure))

        # Square root makes changes in the 0-40 range more visible
        intensity = (pressure / max_pressure) ** 0.5

        red = 255
        green = int(255 * (1 - intensity))
        blue = int(255 * (1 - intensity))

        return f"#{red:02x}{green:02x}{blue:02x}"

    def update(self):
        for sensor_number, cell in self.cells.items():
            value = self.sensor.pressures[sensor_number - 1]
            color = self.pressure_to_color(value)

            cell.config(
                text=f"{sensor_number}\n{value}",
                bg=color
            )


left = FootPressureSensor("Left", "COM7")
right = FootPressureSensor("Right", "COM8")


left_numbers = [
    [12, 24, 36, 48],
    [11, 23, 35, 47],
    [10, 22, 34, 46],
    [9, 21, 33, 45],
    [8, 20, 32, 44],
    [7, 19, 31, 43],
    [6, 18, 30, 42],
    [5, 17, 29, 41],
    [4, 16, 28, 40],
    [3, 15, 27, 39],
    [2, 14, 26, 38],
    [1, 13, 25, 37]
]

right_numbers = [
    [48, 36, 24, 12],
    [47, 35, 23, 11],
    [46, 34, 22, 10],
    [45, 33, 21, 9],
    [44, 32, 20, 8],
    [43, 31, 19, 7],
    [42, 30, 18, 6],
    [41, 29, 17, 5],
    [40, 28, 16, 4],
    [39, 27, 15, 3],
    [38, 26, 14, 2],
    [37, 25, 13, 1]
]

root = tk.Tk()
root.title("Foot Pressure Sensors")

left_grid = FootGrid(root, "Left Foot", left, left_numbers)
right_grid = FootGrid(root, "Right Foot", right, right_numbers)


def update_interface():
    left.update()
    right.update()

    left_grid.update()
    right_grid.update()

    root.after(1, update_interface)


root.after(1, update_interface)
root.mainloop()