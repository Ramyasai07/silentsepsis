#!/usr/bin/env python3
"""Train and evaluate the offline XGBoost candidate on train and validation only."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ai.ml.data_loader import load_processed_dataset
from ai.ml.metrics import evaluate_probabilities, select_threshold

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from xgboost import XGBClassifier
except ModuleNotFoundError as exc:
    XGBClassifier = None
    XGBOOST_IMPORT_ERROR = exc
else:
    XGBOOST_IMPORT_ERROR = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = REPO_ROOT / "ai" / "data" / "processed"
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "ai" / "artifacts" / "xgboost-v1"
MODEL_HYPERPARAMETERS = {
    "n_estimators": 500,
    "learning_rate": 0.05,
    "max_depth": 6,
    "min_child_weight": 1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "eval_metric": "aucpr",
    "early_stopping_rounds": 30,
    "tree_method": "hist",
    "random_state": 42,
    "n_jobs": -1,
}


def train_xgboost(data_root: Path, artifact_root: Path) -> dict[str, object]:
    if XGBClassifier is None:
        raise RuntimeError(
            "XGBoost is required for this command; install requirements-ai.txt"
        ) from XGBOOST_IMPORT_ERROR

    dataset = load_processed_dataset(data_root, split_names=("train", "validation"))
    train = dataset.splits["train"]
    validation = dataset.splits["validation"]

    if train.target.nunique() < 2:
        raise ValueError("Training target must contain both classes")
    if validation.target.nunique() < 2:
        raise ValueError("Validation target must contain both classes")

    negative_count = int((train.target == 0).sum())
    positive_count = int((train.target == 1).sum())
    model = XGBClassifier(
        **MODEL_HYPERPARAMETERS,
        scale_pos_weight=negative_count / positive_count,
    )
    model.fit(
        train.features,
        train.target,
        eval_set=[(validation.features, validation.target)],
        verbose=False,
    )

    validation_probabilities = model.predict_proba(validation.features)[:, 1]
    threshold = select_threshold(validation.target.to_numpy(), validation_probabilities)
    validation_metrics = evaluate_probabilities(
        validation.target.to_numpy(),
        validation_probabilities,
        threshold.threshold,
    )

    artifact_root.mkdir(parents=True, exist_ok=True)
    model.save_model(artifact_root / "model.json")
    metadata = {
        "model_type": "xgboost.XGBClassifier",
        "model_version": artifact_root.name,
        "feature_columns": list(dataset.feature_columns),
        "hyperparameters": {
            **MODEL_HYPERPARAMETERS,
            "scale_pos_weight": negative_count / positive_count,
        },
        "training_rows": int(len(train.target)),
        "validation_rows": int(len(validation.target)),
        "validation_threshold_selection": "max_f1",
        "threshold": threshold.threshold,
        "validation_metrics": validation_metrics,
        "best_iteration": int(model.best_iteration),
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
    print(json.dumps(train_xgboost(args.data_root, args.artifact_root), indent=2))


if __name__ == "__main__":
    main()
