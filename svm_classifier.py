import pandas as pd
import matplotlib.pyplot as plt
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, ConfusionMatrixDisplay
from sklearn.calibration import CalibratedClassifierCV

dataset = "paired2"
DATA_FILE = f"datasets/pressure_training({dataset}).csv"
MODEL_FILE = f"models/pressure_svm({dataset}).pkl"


data = pd.read_csv(DATA_FILE)

labels = ["forward", "backward", "strafe_left", "strafe_right", "none"]
X = data.drop(columns=["label"])
y = data["label"]

print(f"Total samples: {len(data)}\n")
print(f"Samples per class: {y.value_counts()} \n")


X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)


model = Pipeline([
    ("scaler", StandardScaler()),
    ("svm", CalibratedClassifierCV(SVC(kernel="rbf", C=10, gamma="scale"), ensemble=False))
])


model.fit(X_train, y_train)


predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)
print(f"Accuracy: {accuracy * 100:.2f}% \n")

cr = classification_report(y_test, predictions, target_names=labels)
print(f"Classification report:\n{cr}")

cm = confusion_matrix(y_test, predictions, labels=labels)
print(f"Confusion matrix:\n{cm}")

joblib.dump(model, MODEL_FILE)
print(f"\nModel saved to: {MODEL_FILE}")

# disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
# disp.plot(cmap=plt.cm.Blues)
# plt.show()

