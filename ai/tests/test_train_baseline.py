from pathlib import Path

import pandas as pd
import pytest

from ai.scripts.train_baseline import train_baseline


def test_baseline_fails_when_training_target_has_one_class(tmp_path: Path) -> None:
    data_root = tmp_path / "processed"
    data_root.mkdir()
    features = ["feature_1", "feature_2"]
    metadata = {"feature_columns": features, "num_features": 2}
    (data_root / "preprocessing_metadata.json").write_text(
        __import__("json").dumps(metadata), encoding="utf-8"
    )
    frames = {
        "train": pd.DataFrame(
            {
                "patient_id": ["p1", "p2"],
                "feature_1": [1, 2],
                "feature_2": [2, 3],
                "target": [0, 0],
            }
        ),
        "validation": pd.DataFrame(
            {
                "patient_id": ["p3", "p4"],
                "feature_1": [1, 2],
                "feature_2": [2, 3],
                "target": [0, 1],
            }
        ),
        "test": pd.DataFrame(
            {
                "patient_id": ["p5", "p6"],
                "feature_1": [1, 2],
                "feature_2": [2, 3],
                "target": [0, 1],
            }
        ),
    }
    for split, frame in frames.items():
        frame.to_csv(data_root / f"{split}.csv", index=False)

    with pytest.raises(ValueError, match="both classes"):
        train_baseline(data_root, tmp_path / "artifact")
