""" TODO:
 - implement uart w cpp integration
 - predict speed w regression
"""
 
import serial, time, csv, joblib, common
import tkinter as tk
import pandas as pd

class FootPressureSensor:
    def __init__(self, name, port, baud_rate=115200):
        self.name = name
        self.serial = serial.Serial(port, baud_rate, timeout=1)
        self.pressures = [0] * 48

        self.pending_warning = None
        self.bad_checksums = 0
        self.packets_read = 0

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
        if self.packets_read == 0:
            print(f"{self.name}: waiting for packet...")
        packet = self.read_packet()
        if self.packets_read == 0:
            self.packets_read += 1
            print(f"{self.name}: packet read successfully")

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

DIR_DATA_FILE = f"datasets/pressure_training({common.dir_dataset}).csv"
DIR_MODEL_FILE = f"models/pressure_svm({common.dir_dataset}).pkl"
SPD_DATA_FILE = f"datasets/speed_training({common.spd_dataset}).csv"
SPD_MODEL_FILES = {
    "forward": f"models/fwd_spd_svr({common.spd_dataset}).pkl",
    "backward": f"models/bwd_spd_svr({common.spd_dataset}).pkl",
    "strafe_left": f"models/sl_spd_svr({common.spd_dataset}).pkl",
    "strafe_right": f"models/sr_spd_svr({common.spd_dataset}).pkl"
}
dir_model = None
fwd_spd_model = None
bwd_spd_model = None
sl_spd_model = None
sr_spd_model = None
try:
    dir_model = joblib.load(DIR_MODEL_FILE)
    fwd_spd_model = joblib.load(SPD_MODEL_FILES["forward"])
    bwd_spd_model = joblib.load(SPD_MODEL_FILES["backward"])
    sl_spd_model = joblib.load(SPD_MODEL_FILES["strafe_left"])
    sr_spd_model = joblib.load(SPD_MODEL_FILES["strafe_right"])
except FileNotFoundError:
    print("one or more models not found")

CONFIDENCE_THRESHOLD = 0.70

root = tk.Tk()
root.title("Foot Pressure Sensors")
grids_frame = tk.Frame(root)
grids_frame.pack()
dir_btn_frame = tk.Frame(root)
dir_btn_frame.pack(pady=(0, 10))
spd_btn_frame = tk.Frame(root)
spd_btn_frame.pack(pady=(0, 10))

left_grid = FootGrid(grids_frame, "Left Foot", left_sensor, left_indexes)
right_grid = FootGrid(grids_frame, "Right Foot", right_sensor, right_indexes)

btn_width = 10
forward_btn = tk.Button(dir_btn_frame, text="forward", width=btn_width, command=lambda: save_dir_sample("forward"))
backward_btn = tk.Button(dir_btn_frame, text="backward", width=btn_width, command=lambda: save_dir_sample("backward"))
left_btn = tk.Button(dir_btn_frame, text="strafe left", width=btn_width, command=lambda: save_dir_sample("strafe_left"))
right_btn = tk.Button(dir_btn_frame, text="strafe right", width=btn_width, command=lambda: save_dir_sample("strafe_right"))
none_btn = tk.Button(dir_btn_frame, text="none", width=btn_width, command=lambda: save_dir_sample("none"))
undo_btn = tk.Button(dir_btn_frame, text="undo", width=btn_width, command=lambda: undo_last_sample("direction"))
forward_btn.pack(side=tk.LEFT, padx=5)
backward_btn.pack(side=tk.LEFT, padx=5)
left_btn.pack(side=tk.LEFT, padx=5)
right_btn.pack(side=tk.LEFT, padx=5)
none_btn.pack(side=tk.LEFT, padx=5)
undo_btn.pack(side=tk.LEFT, padx=5)

spd0_btn = tk.Button(spd_btn_frame, text="0%", width=btn_width, command=lambda: save_speed_sample(0.0))
spd50_btn = tk.Button(spd_btn_frame, text="50%", width=btn_width, command=lambda: save_speed_sample(0.5))
spd100_btn = tk.Button(spd_btn_frame, text="100%", width=btn_width, command=lambda: save_speed_sample(1.0))
undo_btn = tk.Button(spd_btn_frame, text="undo", width=btn_width, command=lambda: undo_last_sample("speed"))
spd0_btn.pack(side=tk.LEFT, padx=5)
spd50_btn.pack(side=tk.LEFT, padx=5)
spd100_btn.pack(side=tk.LEFT, padx=5)
undo_btn.pack(side=tk.LEFT, padx=5)

prediction_var = tk.StringVar()
prediction_var.set("Prediction: waiting...")
prediction_label = tk.Label(root, textvariable=prediction_var, font=("Arial", 16, "bold"), anchor="center", relief="sunken", padx=8, pady=6)
prediction_label.pack(fill="x", padx=20, pady=(0, 10))
prediction = None

warning_var = tk.StringVar()
warning_var.set("no warnings")
warning_label = tk.Label(root, textvariable=warning_var, font=("Arial", 11), anchor="w", relief="sunken", padx=8, bg="yellow")
warning_label.pack(fill="x", padx=20, pady=(0, 15))

def save_dir_sample(dir):
    row = left_sensor.pressures + right_sensor.pressures + [dir]

    try:
        with open(DIR_DATA_FILE, "x", newline="") as file:
            writer = csv.writer(file)

            header = ([f"left_{i}" for i in range(1, 49)] + [f"right_{i}" for i in range(1, 49)] + ["direction"])

            writer.writerow(header)
            writer.writerow(row)

    except FileExistsError:
        with open(DIR_DATA_FILE, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(row)

    current_time = time.strftime("%H:%M:%S")
    warning_var.set(f"{current_time} | saved training sample: {dir}")

    print(f"saved sample: {dir}")

def save_speed_sample(spd):
    if prediction is None:
        warning_var.set(f"{time.strftime('%H:%M:%S')} | WARNING: no direction identified, sample not saved")
        return

    row = left_sensor.pressures + right_sensor.pressures + [prediction, spd]
    
    try:
        with open(SPD_DATA_FILE, "x", newline="") as file:
            writer = csv.writer(file)

            header = ([f"left_{i}" for i in range(1, 49)] + [f"right_{i}" for i in range(1, 49)] + ["direction", "speed"])

            writer.writerow(header)
            writer.writerow(row)

    except FileExistsError:
        with open(SPD_DATA_FILE, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(row)

    current_time = time.strftime("%H:%M:%S")
    warning_var.set(f"{current_time} | saved training sample: {prediction} speed={spd}")

    print(f"saved sample: {prediction} speed={spd}")

def undo_last_sample(sample_type):
    if sample_type == "direction":
        DATA_FILE = DIR_DATA_FILE
    elif sample_type == "speed":
        DATA_FILE = SPD_DATA_FILE
    try:
        with open(DATA_FILE, "r", newline="") as file:
            rows = list(csv.reader(file))

        if len(rows) <= 1:
            warning_var.set(f"{time.strftime('%H:%M:%S')} | WARNING: no samples to undo")
            return

        removed_row = rows.pop()
        removed_dir = removed_row[-2]
        removed_spd = removed_row[-1]

        with open(DATA_FILE, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(rows)

        warning_var.set(f"{time.strftime('%H:%M:%S')} | removed last sample: {removed_dir} speed={removed_spd}")

        print(f"removed last sample: {removed_dir} speed={removed_spd}")

    except FileNotFoundError:
        warning_var.set(f"{time.strftime('%H:%M:%S')} | WARNING: no training CSV found")

def update_prediction():
    global prediction
    values = left_sensor.pressures + right_sensor.pressures

    columns = (
        [f"left_{i}" for i in range(1, 49)] +
        [f"right_{i}" for i in range(1, 49)]
    )

    sample = pd.DataFrame([values], columns=columns)

    probabilities = dir_model.predict_proba(sample)[0]
    classes = dir_model.classes_

    best_index = probabilities.argmax()
    prediction = classes[best_index]
    confidence = probabilities[best_index]

    if confidence >= CONFIDENCE_THRESHOLD:
        if fwd_spd_model is None or bwd_spd_model is None or sl_spd_model is None or sr_spd_model is None:
            speed = 0
        else:
            if prediction == "forward":
                speed = fwd_spd_model.predict(sample)[0]
            elif prediction == "backward":
                speed = bwd_spd_model.predict(sample)[0]
            elif prediction == "strafe_left":
                speed = sl_spd_model.predict(sample)[0]
            elif prediction == "strafe_right":
                speed = sr_spd_model.predict(sample)[0]
            else:
                speed = 0

        speed = max(0.0, min(speed, 1.0))
        prediction_var.set(f"Prediction: {prediction} ({confidence * 100:.1f}%) | Speed: {speed * 100:.1f}%")
    else:
        prediction = None
        prediction_var.set(f"No direction identified ({confidence * 100:.1f}%)")

flush_count = 0
last_stats_print = time.time()
def update_interface():
    global last_stats_print, flush_count

    left_sensor.update()
    right_sensor.update()

    left_grid.update()
    right_grid.update()

    if dir_model is None:
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
            flush_count += 1
            bytes_waiting = left_sensor.flush()
            current_time = time.strftime("%H:%M:%S")
            warning_var.set(f"{current_time} | WARNING: left input buffer flushed {bytes_waiting} bytes ({flush_count})")

        if right_sensor.serial.in_waiting > 100:
            bytes_waiting = right_sensor.flush()
            current_time = time.strftime("%H:%M:%S")
            warning_var.set(f"{current_time} | WARNING: right input buffer flushed {bytes_waiting} bytes ({flush_count})")

        last_stats_print = time.time()

    root.after(1, update_interface)

root.after(1, update_interface)
root.mainloop()