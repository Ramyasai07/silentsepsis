import json
from pathlib import Path

import pandas as pd
import pytest

from ai.ml.data_loader import load_processed_dataset
from ai.scripts import train_xgboost


def _write_dataset(data_root: Path) -> None:
    data_root.mkdir()
    metadata = {"feature_columns": ["feature_1", "feature_2"], "num_features": 2}
    (data_root / "preprocessing_metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    frames = {
        "train": pd.DataFrame({"patient_id": ["p1", "p2", "p3", "p4"], "feature_1": [0, 0, 1, 1], "feature_2": [0, 1, 0, 1], "target": [0, 0, 1, 1]}),
        "validation": pd.DataFrame({"patient_id": ["p5", "p6", "p7", "p8"], "feature_1": [0, 0, 1, 1], "feature_2": [0, 1, 0, 1], "target": [0, 0, 1, 1]}),
    }
    for split, frame in frames.items():
        frame.to_csv(data_root / f"{split}.csv", index=False)


def test_loader_can_select_train_and_validation_without_test(tmp_path: Path) -> None:
    data_root = tmp_path / "processed"
    _write_dataset(data_root)

    dataset = load_processed_dataset(data_root, split_names=("train", "validation"))

    assert tuple(dataset.splits) == ("train", "validation")
    assert not (data_root / "test.csv").exists()

    overlapping = pd.read_csv(data_root / "validation.csv")
    overlapping.loc[0, "patient_id"] = "p1"
    overlapping.to_csv(data_root / "validation.csv", index=False)

    with pytest.raises(ValueError, match="Patient leakage detected"):
        load_processed_dataset(data_root, split_names=("train", "validation"))


@pytest.mark.skipif(train_xgboost.XGBClassifier is None, reason="xgboost is not installed")
def test_xgboost_training_writes_reloadable_artifact(tmp_path: Path) -> None:
    _write_dataset(tmp_path / "processed")

    metadata = train_xgboost.train_xgboost(
        tmp_path / "processed",
        tmp_path / "artifact",
    )

    assert len(metadata["feature_columns"]) == 2
    assert metadata["training_rows"] == 4
    assert metadata["validation_rows"] == 4
    assert (tmp_path / "artifact" / "model.json").exists()
    assert (tmp_path / "artifact" / "metadata.json").exists()

    reloaded = train_xgboost.XGBClassifier()
    reloaded.load_model(tmp_path / "artifact" / "model.json")
    assert reloaded.get_booster().feature_names == ["feature_1", "feature_2"]


def test_xgboost_training_requires_dependency(tmp_path: Path) -> None:
    if train_xgboost.XGBClassifier is not None:
        pytest.skip("dependency is installed")

    with pytest.raises(RuntimeError, match="XGBoost is required"):
        train_xgboost.train_xgboost(tmp_path / "processed", tmp_path / "artifact")