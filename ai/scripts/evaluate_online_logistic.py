from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import joblib
import numpy as np
import pandas as pd

from ai.ml.metrics import evaluate_probabilities


ROOT = Path(__file__).resolve().parents[2]

ARTIFACT = ROOT / "ai/artifacts/online-logistic-v1-calibrated"
SOURCE = ROOT / "ai/artifacts/online-logistic-v1"
DATA = ROOT / "ai/data/processed_online"

OUTPUT = ARTIFACT / "test_evaluation.json"

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

metadata = json.loads(
    (ARTIFACT / "metadata.json").read_text(encoding="utf-8")
)

source_metadata = json.loads(
    (SOURCE / "metadata.json").read_text(encoding="utf-8")
)

model_path = SOURCE / "model.joblib"
imputer_path = SOURCE / "imputer.joblib"
calibrator_path = ARTIFACT / "platt_calibrator.joblib"
test_path = DATA / "test.csv"

expected_model_hash = metadata["provenance"]["source_model_sha256"]
actual_model_hash = hashlib.sha256(
    model_path.read_bytes()
).hexdigest()

if actual_model_hash != expected_model_hash:
    raise ValueError("Source model checksum mismatch")

expected_imputer_hash = metadata["provenance"]["source_imputer_sha256"]
actual_imputer_hash = hashlib.sha256(
    imputer_path.read_bytes()
).hexdigest()

if actual_imputer_hash != expected_imputer_hash:
    raise ValueError("Source imputer checksum mismatch")

feature_columns = metadata["feature_columns"]

test = pd.read_csv(test_path)

expected_columns = [
    "patient_id",
    *feature_columns,
    "target",
]

if list(test.columns) != expected_columns:
    raise ValueError("Test schema does not match frozen online schema")

model = joblib.load(model_path)
imputer = joblib.load(imputer_path)
calibrator = joblib.load(calibrator_path)

X_test = test.loc[:, feature_columns].astype(np.float32)
y_test = test["target"].astype(np.int8).to_numpy()

X_test_imputed = imputer.transform(X_test)

raw_probabilities = model.predict_proba(
    X_test_imputed
)[:, 1]

clipped = np.clip(raw_probabilities, 1e-6, 1 - 1e-6)
logits = np.log(clipped / (1 - clipped))

calibrated_probabilities = calibrator.predict_proba(
    logits.reshape(-1, 1)
)[:, 1]

threshold = float(metadata["threshold"])

row_metrics = evaluate_probabilities(
    y_test,
    calibrated_probabilities,
    threshold,
)

patient_values = {}

for patient_id, target, probability in zip(
    test["patient_id"].astype(str),
    y_test,
    calibrated_probabilities,
):
    values = patient_values.setdefault(patient_id, [0, 0.0])
    values[0] = max(values[0], int(target))
    values[1] = max(values[1], float(probability))

patient_targets = np.array(
    [v[0] for v in patient_values.values()]
)

patient_probabilities = np.array(
    [v[1] for v in patient_values.values()]
)

patient_metrics = evaluate_probabilities(
    patient_targets,
    patient_probabilities,
    threshold,
)

result = {
    "evaluation_type": "locked_test_evaluation",
    "model_version": metadata["model_version"],
    "source_model_version": source_metadata["model_version"],
    "calibration_method": metadata["calibration_method"],
    "feature_columns": feature_columns,
    "num_features": len(feature_columns),
    "threshold": threshold,
    "test_rows": int(len(test)),
    "test_patients": int(test["patient_id"].nunique()),
    "positive_row_count": int(y_test.sum()),
    "positive_patient_count": int(patient_targets.sum()),
    "row_level": row_metrics,
    "patient_level": patient_metrics,
    "provenance": {
        "test_read_for_locked_evaluation": True,
        "training_performed": False,
        "calibrator_fitted": False,
        "threshold_tuned": False,
        "model_sha256": actual_model_hash,
        "imputer_sha256": actual_imputer_hash,
        "calibrator_sha256": hashlib.sha256(
            calibrator_path.read_bytes()
        ).hexdigest(),
    },
    "created_at": datetime.now(timezone.utc).isoformat(),
}

OUTPUT.write_text(
    json.dumps(result, indent=2),
    encoding="utf-8",
)

print(json.dumps(result, indent=2))

