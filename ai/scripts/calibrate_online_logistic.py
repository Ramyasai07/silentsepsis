from __future__ import annotations

import hashlib
import json
from pathlib import Path

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from ai.ml.metrics import evaluate_probabilities, select_threshold


def calibrate_online_logistic(
    artifact_root: Path,
    data_root: Path,
    calibrated_root: Path,
) -> dict:
    metadata_path = artifact_root / "metadata.json"
    model_path = artifact_root / "model.joblib"
    imputer_path = artifact_root / "imputer.joblib"

    if not metadata_path.exists():
        raise FileNotFoundError(metadata_path)
    if not model_path.exists():
        raise FileNotFoundError(model_path)
    if not imputer_path.exists():
        raise FileNotFoundError(imputer_path)

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    validation_path = data_root / "validation.csv"
    if not validation_path.exists():
        raise FileNotFoundError(validation_path)

    import pandas as pd

    validation = pd.read_csv(validation_path)

    feature_columns = metadata["feature_columns"]
    expected_columns = ["patient_id", *feature_columns, "target"]

    if list(validation.columns) != expected_columns:
        raise ValueError("Validation schema does not match model metadata")

    model = joblib.load(model_path)
    imputer = joblib.load(imputer_path)

    X = validation.loc[:, feature_columns].astype(np.float32)
    y = validation["target"].astype(np.int8).to_numpy()

    X_imputed = imputer.transform(X)
    raw_probabilities = model.predict_proba(X_imputed)[:, 1]

    patient_ids = validation["patient_id"].astype(str).to_numpy()
    patients = np.array(sorted(set(patient_ids)))

    calibration_patients = set(patients[::2])
    calibration_mask = np.isin(patient_ids, list(calibration_patients))
    assessment_mask = ~calibration_mask

    calibration_probabilities = raw_probabilities[calibration_mask]
    calibration_targets = y[calibration_mask]

    assessment_probabilities = raw_probabilities[assessment_mask]
    assessment_targets = y[assessment_mask]

    def logits(probabilities: np.ndarray) -> np.ndarray:
        clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
        return np.log(clipped / (1 - clipped))

    calibrator = LogisticRegression(
        C=1e6,
        solver="lbfgs",
        max_iter=1000,
    )

    calibration_logits = logits(calibration_probabilities).reshape(-1, 1)
    assessment_logits = logits(assessment_probabilities).reshape(-1, 1)

    calibrator.fit(calibration_logits, calibration_targets)

    calibrated_assessment = calibrator.predict_proba(
        assessment_logits
    )[:, 1]

    raw_threshold = select_threshold(
        calibration_targets,
        calibration_probabilities,
    )

    calibrated_calibration = calibrator.predict_proba(
        calibration_logits
    )[:, 1]

    calibrated_threshold = select_threshold(
        calibration_targets,
        calibrated_calibration,
    )

    raw_metrics = evaluate_probabilities(
        assessment_targets,
        assessment_probabilities,
        raw_threshold.threshold,
    )

    calibrated_metrics = evaluate_probabilities(
        assessment_targets,
        calibrated_assessment,
        calibrated_threshold.threshold,
    )

    calibrated_root.mkdir(parents=True, exist_ok=True)

    calibrator_path = calibrated_root / "platt_calibrator.joblib"
    output_metadata = calibrated_root / "metadata.json"

    joblib.dump(calibrator, calibrator_path)

    result = {
        "model_version": "online-logistic-v1-calibrated",
        "source_model_version": metadata["model_version"],
        "calibration_method": "platt_scaling",
        "feature_columns": feature_columns,
        "num_features": len(feature_columns),
        "calibration_split": {
            "method": "sorted_patient_ids[::2]",
            "calibration_patients": len(calibration_patients),
            "calibration_rows": int(calibration_mask.sum()),
            "assessment_patients": int(
                len(patients) - len(calibration_patients)
            ),
            "assessment_rows": int(assessment_mask.sum()),
        },
        "threshold": float(calibrated_threshold.threshold),
        "threshold_selection": "calibration_split_max_f1",
        "raw_assessment_metrics": raw_metrics,
        "calibrated_assessment_metrics": calibrated_metrics,
        "provenance": {
            "validation_only": True,
            "test_read": False,
            "training_performed": False,
            "source_model_sha256": hashlib.sha256(
                model_path.read_bytes()
            ).hexdigest(),
            "source_imputer_sha256": hashlib.sha256(
                imputer_path.read_bytes()
            ).hexdigest(),
        },
    }

    output_metadata.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    return result


def main() -> None:
    result = calibrate_online_logistic(
        Path("ai/artifacts/online-logistic-v1"),
        Path("ai/data/processed_online"),
        Path("ai/artifacts/online-logistic-v1-calibrated"),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

