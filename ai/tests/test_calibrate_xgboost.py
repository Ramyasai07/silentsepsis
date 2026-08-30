import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from ai.ml.calibration import calibrate_probabilities, fit_platt_calibrator
from ai.scripts.calibrate_xgboost import calibrate_xgboost


def _write_validation_data(data_root: Path) -> None:
    data_root.mkdir()
    features = ["feature_1", "feature_2"]
    (data_root / "preprocessing_metadata.json").write_text(
        json.dumps({"feature_columns": features, "num_features": 2}),
        encoding="utf-8",
    )
    frame = pd.DataFrame({
        "patient_id": ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"],
        "feature_1": [0, 0, 1, 1, 0, 0, 1, 1],
        "feature_2": [0, 1, 0, 1, 0, 1, 0, 1],
        "target": [0, 0, 1, 1, 0, 0, 1, 1],
    })
    frame.to_csv(data_root / "validation.csv", index=False)


@pytest.mark.skipif(
    __import__("ai.scripts.calibrate_xgboost", fromlist=["XGBClassifier"]).XGBClassifier
    is None,
    reason="xgboost is not installed",
)
def test_calibrated_artifact_reloads_and_preserves_schema(tmp_path: Path) -> None:
    source_root = tmp_path / "xgboost-v1"
    source_root.mkdir()
    from xgboost import XGBClassifier

    model = XGBClassifier(n_estimators=3, max_depth=2, eval_metric="logloss")
    features = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    model.fit(features, np.array([0, 0, 1, 1]))
    model.save_model(source_root / "model.json")
    (source_root / "metadata.json").write_text(
        json.dumps({"model_version": "xgboost-v1", "feature_columns": ["feature_1", "feature_2"]}),
        encoding="utf-8",
    )
    data_root = tmp_path / "processed"
    _write_validation_data(data_root)

    metadata = calibrate_xgboost(data_root, source_root, tmp_path / "calibrated")
    calibrator = joblib.load(tmp_path / "calibrated" / "platt_calibrator.joblib")
    probabilities = calibrate_probabilities(calibrator, np.array([0.1, 0.9]))

    assert probabilities.shape == (2,)
    assert metadata["feature_columns"] == ["feature_1", "feature_2"]
    assert metadata["threshold"] == metadata["validation_metrics"]["calibrated"]["threshold"]


def test_platt_calibrator_generates_reloadable_probabilities(tmp_path: Path) -> None:
    calibrator = fit_platt_calibrator(
        np.array([0.1, 0.2, 0.8, 0.9]),
        np.array([0, 0, 1, 1]),
    )
    path = tmp_path / "calibrator.joblib"
    joblib.dump(calibrator, path)
    reloaded = joblib.load(path)

    probabilities = calibrate_probabilities(reloaded, np.array([0.1, 0.9]))
    assert probabilities.shape == (2,)
    assert np.all((probabilities >= 0) & (probabilities <= 1))