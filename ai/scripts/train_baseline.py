#!/usr/bin/env python3
"""Train and evaluate the offline LogisticRegression baseline."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression

from ai.ml.data_loader import load_processed_dataset
from ai.ml.metrics import evaluate_probabilities, select_threshold

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = REPO_ROOT / "ai" / "data" / "processed"
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "ai" / "artifacts" / "logistic-regression-v1"


def train_baseline(data_root: Path, artifact_root: Path) -> dict[str, object]:
    dataset = load_processed_dataset(data_root)
    train = dataset.splits["train"]
    validation = dataset.splits["validation"]

    if train.target.nunique() < 2:
        raise ValueError("Training target must contain both classes")
    if validation.target.nunique() < 2:
        raise ValueError("Validation target must contain both classes")

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=200,
        solver="lbfgs",
        random_state=42,
    )
    model.fit(train.features, train.target)

    validation_probabilities = model.predict_proba(validation.features)[:, 1]
    threshold = select_threshold(validation.target.to_numpy(), validation_probabilities)
    validation_metrics = evaluate_probabilities(
        validation.target.to_numpy(),
        validation_probabilities,
        threshold.threshold,
    )

    artifact_root.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, artifact_root / "model.joblib")
    metadata = {
        "model_type": "sklearn.linear_model.LogisticRegression",
        "model_version": artifact_root.name,
        "feature_columns": list(dataset.feature_columns),
        "class_weight": "balanced",
        "random_state": 42,
        "validation_threshold_selection": "max_f1",
        "threshold": threshold.threshold,
        "validation_metrics": validation_metrics,
        "training_rows": int(len(train.target)),
        "validation_rows": int(len(validation.target)),
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
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    args = parser.parse_args()

    metadata = train_baseline(args.data_root, args.artifact_root)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
