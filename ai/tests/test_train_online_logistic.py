from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai.ml.online_preprocessing import ONLINE_FEATURE_COLUMNS
from ai.scripts.train_online_logistic import train_online_logistic


def make_frame(patient_ids: list[str], targets: list[int]) -> pd.DataFrame:
    rows = []

    for patient_id, target in zip(patient_ids, targets):
        rows.append(
            {
                "patient_id": patient_id,
                "HR": 60 if target == 0 else 120,
                "O2Sat": 98,
                "Temp": 36.5 if target == 0 else 38.5,
                "SBP": 120,
                "DBP": 80,
                "Resp": 16 if target == 0 else 24,
                "MAP": 93.333333,
                "Age": 25,
                "Gender": 1,
                "HR_missing": 0,
                "O2Sat_missing": 0,
                "Temp_missing": 0,
                "SBP_missing": 0,
                "DBP_missing": 0,
                "Resp_missing": 0,
                "target": target,
            }
        )

    return pd.DataFrame(rows)


def write_dataset(root: Path) -> None:
    root.mkdir(parents=True)

    metadata = {
        "feature_columns": list(ONLINE_FEATURE_COLUMNS),
        "num_features": len(ONLINE_FEATURE_COLUMNS),
    }

    (root / "preprocessing_metadata.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    train = make_frame(
        ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"],
        [0, 0, 0, 0, 1, 1, 1, 1],
    )

    validation = make_frame(
        ["p9", "p10", "p11", "p12", "p13", "p14", "p15", "p16"],
        [0, 0, 0, 0, 1, 1, 1, 1],
    )

    train.to_csv(root / "train.csv", index=False)
    validation.to_csv(root / "validation.csv", index=False)


def test_online_logistic_trains_serializes_and_reloads(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "processed_online"
    artifact_root = tmp_path / "artifact"

    write_dataset(data_root)

    metadata = train_online_logistic(
        data_root,
        artifact_root,
    )

    assert metadata["num_features"] == 15
    assert metadata["feature_columns"] == list(
        ONLINE_FEATURE_COLUMNS
    )

    assert (artifact_root / "model.joblib").exists()
    assert (artifact_root / "metadata.json").exists()

    saved = json.loads(
        (artifact_root / "metadata.json").read_text(
            encoding="utf-8"
        )
    )

    assert saved["num_features"] == 15
    assert saved["model_version"] == "online-logistic-v1"


def test_online_logistic_uses_only_train_and_validation(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "processed_online"
    artifact_root = tmp_path / "artifact"

    write_dataset(data_root)

    # Deliberately do not create test.csv.
    train_online_logistic(
        data_root,
        artifact_root,
    )

    assert not (data_root / "test.csv").exists()
    assert (artifact_root / "model.joblib").exists()
    assert (artifact_root / "metadata.json").exists()