#!/usr/bin/env python3
"""Create a validation-calibrated artifact from xgboost-v1."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from xgboost import XGBClassifier

from ai.ml.calibration import calibrate_probabilities, fit_platt_calibrator
from ai.ml.data_loader import load_processed_dataset
from ai.ml.metrics import evaluate_probabilities, select_threshold

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = REPO_ROOT / "ai" / "data" / "processed"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "ai" / "artifacts" / "xgboost-v1"
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "ai" / "artifacts" / "xgboost-v1-calibrated"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def patient_level_metrics(
    patient_ids: np.ndarray,
    targets: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, object]:
    patient_values: dict[str, list[float]] = {}
    for patient_id, target, probability in zip(patient_ids, targets, probabilities):
        values = patient_values.setdefault(str(patient_id), [0.0, 0.0])
        values[0] = max(values[0], float(target))
        values[1] = max(values[1], float(probability))

    patient_targets = np.array([values[0] for values in patient_values.values()])
    patient_probabilities = np.array([values[1] for values in patient_values.values()])
    return evaluate_probabilities(patient_targets, patient_probabilities, threshold)


def calibrate_xgboost(
    data_root: Path,
    source_root: Path,
    artifact_root: Path,
) -> dict[str, object]:
    source_model_path = source_root / "model.json"
    source_metadata_path = source_root / "metadata.json"
    if not source_model_path.exists() or not source_metadata_path.exists():
        raise FileNotFoundError(f"Incomplete source artifact: {source_root}")

    source_metadata = json.loads(source_metadata_path.read_text(encoding="utf-8"))
    dataset = load_processed_dataset(data_root, split_names=("validation",))
    validation = dataset.splits["validation"]
    if list(dataset.feature_columns) != source_metadata["feature_columns"]:
        raise ValueError("Validation feature schema differs from source model schema")

    model = XGBClassifier()
    model.load_model(source_model_path)
    raw_probabilities = model.predict_proba(validation.features)[:, 1]
    targets = validation.target.to_numpy()
    patient_ids = validation.patient_ids.to_numpy()

    patients = np.array(sorted(set(patient_ids)))
    calibration_patients = set(patients[::2])
    calibration_rows = np.isin(patient_ids, list(calibration_patients))
    evaluation_rows = ~calibration_rows

    calibrator = fit_platt_calibrator(
        raw_probabilities[calibration_rows],
        targets[calibration_rows],
    )
    calibrated_calibration = calibrate_probabilities(
        calibrator,
        raw_probabilities[calibration_rows],
    )
    calibrated_evaluation = calibrate_probabilities(
        calibrator,
        raw_probabilities[evaluation_rows],
    )
    raw_evaluation = raw_probabilities[evaluation_rows]
    evaluation_targets = targets[evaluation_rows]
    evaluation_patient_ids = patient_ids[evaluation_rows]

    raw_threshold = select_threshold(
        targets[calibration_rows],
        raw_probabilities[calibration_rows],
    )
    calibrated_threshold = select_threshold(
        targets[calibration_rows],
        calibrated_calibration,
    )
    validation_metrics = {
        "raw": evaluate_probabilities(
            evaluation_targets,
            raw_evaluation,
            raw_threshold.threshold,
        ),
        "calibrated": evaluate_probabilities(
            evaluation_targets,
            calibrated_evaluation,
            calibrated_threshold.threshold,
        ),
        "raw_patient": patient_level_metrics(
            evaluation_patient_ids,
            evaluation_targets,
            raw_evaluation,
            raw_threshold.threshold,
        ),
        "calibrated_patient": patient_level_metrics(
            evaluation_patient_ids,
            evaluation_targets,
            calibrated_evaluation,
            calibrated_threshold.threshold,
        ),
    }

    artifact_root.mkdir(parents=True, exist_ok=True)
    joblib.dump(calibrator, artifact_root / "platt_calibrator.joblib")
    metadata = {
        "model_version": artifact_root.name,
        "source_model_version": source_metadata["model_version"],
        "model_reference": "../xgboost-v1/model.json",
        "model_reference_sha256": sha256_file(source_model_path),
        "source_metadata_sha256": sha256_file(source_metadata_path),
        "calibration_method": "platt_scaling",
        "feature_columns": list(dataset.feature_columns),
        "calibration_split": {
            "source": "validation.csv only",
            "patient_order": "sorted unique patient IDs",
            "calibration_selection": "patients[::2]",
            "calibration_patients": len(calibration_patients),
            "calibration_rows": int(calibration_rows.sum()),
            "evaluation_patients": len(patients) - len(calibration_patients),
            "evaluation_rows": int(evaluation_rows.sum()),
        },
        "threshold": calibrated_threshold.threshold,
        "validation_metrics": validation_metrics,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (artifact_root / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    args = parser.parse_args()
    print(
        json.dumps(
            calibrate_xgboost(args.data_root, args.source_root, args.artifact_root),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
