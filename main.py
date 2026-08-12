import serial, time, csv, joblib
import tkinter as tk
import pandas as pd

class FootPressureSensor:
    def __init__(self, name, port, baud_rate=115200):
        self.name = name
        self.serial = serial.Serial(port, baud_rate, timeout=1)
        self.pressures = [0] * 48

        self.pending_warning = None
        self.bad_checksums = 0


    def read_packet(self):
        while True:
            first_byte = self.serial.read(1)
            if first_byte != b"\x40":
                continue

            remaining = self.serial.read(98)

            packet = b"\x40" + remaining

            if len(packet) != 99:
                continue

            calculated_checksum = sum(packet[:98]) & 0xFF
            received_checksum = packet[98]

            if calculated_checksum != received_checksum:
                self.bad_checksums += 1
                current_time = time.strftime("%H:%M:%S")
                self.pending_warning = f"{current_time} | WARNING: {self.name} foot bad checksum"
                print(f"{self.name}: bad checksum")
                continue

            return packet

    def update(self):
        packet = self.read_packet()

        for i in range(48):
            high = packet[2 + i * 2]
            low = packet[3 + i * 2]
            self.pressures[i] = (high << 8) | low

    def log(self):
        print(f"{self.name:5} | in_waiting: {self.serial.in_waiting:3} | bad checksums: {self.bad_checksums}")

    def flush(self):
        bytes_waiting = self.serial.in_waiting
        self.serial.reset_input_buffer()
        print(f"{self.name}: flushed input buffer ({bytes_waiting} bytes)")

        return bytes_waiting


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
                    width=6,
                    height=2,
                    font=("Arial", 11, "bold"),
                    relief="solid",
                    borderwidth=1,
                    bg="white"
                )

                cell.grid(row=row, column=col, padx=2, pady=2)
                self.cells[sensor_number] = cell

    def pressure_to_color(self, pressure):
        max_pressure = 500
        pressure = max(0, min(pressure, max_pressure))

        intensity_scale = 0.5
        intensity = (pressure / max_pressure) ** intensity_scale

        red = 255
        green = int(255 * (1 - intensity))
        blue = int(255 * (1 - intensity))

        return f"#{red:02x}{green:02x}{blue:02x}"

    def update(self):
        for sensor_number, cell in self.cells.items():
            value = self.sensor.pressures[sensor_number - 1]
            color = self.pressure_to_color(value)

            cell.config(text=f"{value}", bg=color)


left_sensor = FootPressureSensor("left", "COM7")
right_sensor = FootPressureSensor("right", "COM8")

left_indexes = [
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

right_indexes = [
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

dataset = "paired2"
DATA_FILE = f"datasets/pressure_training({dataset}).csv"
MODEL_FILE = f"models/pressure_svm({dataset}).pkl"
model = None
try:
    model = joblib.load(MODEL_FILE)
except FileNotFoundError:
    print("No model found")

CONFIDENCE_THRESHOLD = 0.70

root = tk.Tk()
root.title("Foot Pressure Sensors")
grids_frame = tk.Frame(root)
grids_frame.pack()
btn_frame = tk.Frame(root)
btn_frame.pack(pady=(0, 10))

left_grid = FootGrid(grids_frame, "Left Foot", left_sensor, left_indexes)
right_grid = FootGrid(grids_frame, "Right Foot", right_sensor, right_indexes)

btn_width = 10
forward_btn = tk.Button(btn_frame, text="forward", width=btn_width, command=lambda: save_sample("forward"))
backward_btn = tk.Button(btn_frame, text="backward", width=btn_width, command=lambda: save_sample("backward"))
left_btn = tk.Button(btn_frame, text="strafe left", width=btn_width, command=lambda: save_sample("strafe_left"))
right_btn = tk.Button(btn_frame, text="strafe right", width=btn_width, command=lambda: save_sample("strafe_right"))
none_btn = tk.Button(btn_frame, text="none", width=btn_width, command=lambda: save_sample("none"))
undo_btn = tk.Button(btn_frame, text="undo", width=btn_width, command=lambda: undo_last_sample())
forward_btn.pack(side=tk.LEFT, padx=5)
backward_btn.pack(side=tk.LEFT, padx=5)
left_btn.pack(side=tk.LEFT, padx=5)
right_btn.pack(side=tk.LEFT, padx=5)
none_btn.pack(side=tk.LEFT, padx=5)
undo_btn.pack(side=tk.LEFT, padx=5)

prediction_var = tk.StringVar()
prediction_var.set("Prediction: waiting...")
prediction_label = tk.Label(root, textvariable=prediction_var, font=("Arial", 16, "bold"), anchor="center", relief="sunken", padx=8, pady=6)
prediction_label.pack(fill="x", padx=20, pady=(0, 10))

warning_var = tk.StringVar()
warning_var.set("no warnings")
warning_label = tk.Label(root, textvariable=warning_var, font=("Arial", 11), anchor="w", relief="sunken", padx=8, bg="yellow")
warning_label.pack(fill="x", padx=20, pady=(0, 15))


def save_sample(label):
    row = left_sensor.pressures + right_sensor.pressures + [label]

    try:
        with open(DATA_FILE, "x", newline="") as file:
            writer = csv.writer(file)

            header = ([f"left_{i}" for i in range(1, 49)] + [f"right_{i}" for i in range(1, 49)] + ["label"])

            writer.writerow(header)
            writer.writerow(row)

    except FileExistsError:
        with open(DATA_FILE, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(row)

    current_time = time.strftime("%H:%M:%S")
    warning_var.set(f"{current_time} | saved training sample: {label}")

    print(f"saved sample: {label}")

def undo_last_sample():
    try:
        with open(DATA_FILE, "r", newline="") as file:
            rows = list(csv.reader(file))

        if len(rows) <= 1:
            warning_var.set(f"{time.strftime('%H:%M:%S')} | WARNING: no samples to undo")
            return

        removed_row = rows.pop()
        removed_label = removed_row[-1]

        with open(DATA_FILE, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(rows)

        warning_var.set(f"{time.strftime('%H:%M:%S')} | removed last sample: {removed_label}")

        print(f"removed last sample: {removed_label}")

    except FileNotFoundError:
        warning_var.set(f"{time.strftime('%H:%M:%S')} | WARNING: no training CSV found")

def update_prediction():
    values = left_sensor.pressures + right_sensor.pressures

    columns = (
        [f"left_{i}" for i in range(1, 49)] +
        [f"right_{i}" for i in range(1, 49)]
    )

    sample = pd.DataFrame([values], columns=columns)

    probabilities = model.predict_proba(sample)[0]
    classes = model.classes_

    best_index = probabilities.argmax()
    prediction = classes[best_index]
    confidence = probabilities[best_index]

    if confidence >= CONFIDENCE_THRESHOLD:
        prediction_var.set(f"Prediction: {prediction} ({confidence * 100:.1f}%)")
    else:
        prediction_var.set(f"No direction identified ({confidence * 100:.1f}%)")

last_stats_print = time.time()
def update_interface():
    global last_stats_print

    left_sensor.update()
    right_sensor.update()

    left_grid.update()
    right_grid.update()

    if model is None:
        prediction_var.set("Prediction: no model loaded")
    else:
        update_prediction()

    if left_sensor.pending_warning is not None:
        warning_var.set(left_sensor.pending_warning)
        left_sensor.pending_warning = None

    if right_sensor.pending_warning is not None:
        warning_var.set(right_sensor.pending_warning)
        right_sensor.pending_warning = None

    if time.time() - last_stats_print >= 1:
        # left_sensor.log()
        # right_sensor.log()

        if left_sensor.serial.in_waiting > 100:
            bytes_waiting = left_sensor.flush()
            current_time = time.strftime("%H:%M:%S")
            warning_var.set(f"{current_time} | WARNING: left input buffer flushed ({bytes_waiting} bytes)")

        if right_sensor.serial.in_waiting > 100:
            bytes_waiting = right_sensor.flush()
            current_time = time.strftime("%H:%M:%S")
            warning_var.set(f"{current_time} | WARNING: right input buffer flushed ({bytes_waiting} bytes)")

        print()
        last_stats_print = time.time()

    root.after(1, update_interface)

root.after(1, update_interface)
root.mainloop()