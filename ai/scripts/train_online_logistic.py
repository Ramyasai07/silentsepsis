from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.ml.metrics import evaluate_probabilities, select_threshold
from ai.ml.online_preprocessing import ONLINE_FEATURE_COLUMNS


def load_online_splits(
    data_root: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load only train and validation online-model splits."""

    metadata_path = data_root / "preprocessing_metadata.json"

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata not found: {metadata_path}"
        )

    metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )

    feature_columns = tuple(metadata["feature_columns"])

    if feature_columns != ONLINE_FEATURE_COLUMNS:
        raise ValueError(
            "Online feature schema does not match metadata"
        )

    if metadata["num_features"] != len(ONLINE_FEATURE_COLUMNS):
        raise ValueError(
            "Online feature count does not match metadata"
        )

    expected_columns = [
        "patient_id",
        *ONLINE_FEATURE_COLUMNS,
        "target",
    ]

    splits: dict[str, pd.DataFrame] = {}

    # Deliberately load ONLY train and validation.
    # test.csv must not be touched during training.
    for split_name in ("train", "validation"):
        path = data_root / f"{split_name}.csv"

        if not path.exists():
            raise FileNotFoundError(
                f"Missing split: {path}"
            )

        frame = pd.read_csv(path)

        if list(frame.columns) != expected_columns:
            raise ValueError(
                f"{split_name}: columns do not match online schema"
            )

        if frame["patient_id"].isna().any():
            raise ValueError(
                f"{split_name}: patient_id contains missing values"
            )

        if frame["target"].isna().any():
            raise ValueError(
                f"{split_name}: target contains missing values"
            )

        if not set(frame["target"].unique()).issubset({0, 1}):
            raise ValueError(
                f"{split_name}: target must contain only 0 and 1"
            )

        splits[split_name] = frame

    train_patients = set(
        splits["train"]["patient_id"]
    )
    validation_patients = set(
        splits["validation"]["patient_id"]
    )

    overlap = train_patients & validation_patients

    if overlap:
        raise ValueError(
            "Patient leakage between train and validation: "
            f"{len(overlap)} patients"
        )

    return (
        splits["train"],
        splits["validation"],
        metadata,
    )


def train_online_logistic(
    data_root: Path,
    artifact_root: Path,
) -> dict:
    """Train the stateless online-compatible Logistic Regression model."""

    train, validation, metadata = load_online_splits(
        data_root
    )

    X_train = train.loc[
        :, ONLINE_FEATURE_COLUMNS
    ].astype(np.float32)

    y_train = train["target"].astype(np.int8)

    X_validation = validation.loc[
        :, ONLINE_FEATURE_COLUMNS
    ].astype(np.float32)

    y_validation = validation["target"].astype(np.int8)

    # ---------------------------------------------------------
    # TRAIN-ONLY MEDIAN IMPUTATION
    # ---------------------------------------------------------
    #
    # The online feature transformer intentionally preserves
    # missing clinical measurements as NaN.
    #
    # The imputer learns statistics ONLY from training data.
    # Validation is transformed using those frozen statistics.
    #
    # This prevents validation leakage and gives runtime a
    # deterministic preprocessing artifact.
    # ---------------------------------------------------------

    imputer = SimpleImputer(strategy="median")

    X_train_imputed = imputer.fit_transform(
        X_train
    )

    X_validation_imputed = imputer.transform(
        X_validation
    )

    if np.isnan(X_train_imputed).any():
        raise ValueError(
            "Imputed train features still contain NaN"
        )

    if np.isnan(X_validation_imputed).any():
        raise ValueError(
            "Imputed validation features still contain NaN"
        )

    # ---------------------------------------------------------
    # MODEL
    # ---------------------------------------------------------

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=3000,
        random_state=42,
    )

    model.fit(
        X_train_imputed,
        y_train,
    )

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    validation_probabilities = model.predict_proba(
        X_validation_imputed
    )[:, 1]

    threshold_result = select_threshold(
        y_validation.to_numpy(),
        validation_probabilities,
    )

    metrics = evaluate_probabilities(
        y_validation.to_numpy(),
        validation_probabilities,
        threshold_result.threshold,
    )

    # ---------------------------------------------------------
    # ARTIFACTS
    # ---------------------------------------------------------

    artifact_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    model_path = artifact_root / "model.joblib"
    imputer_path = artifact_root / "imputer.joblib"
    metadata_path = artifact_root / "metadata.json"

    joblib.dump(
        model,
        model_path,
    )

    joblib.dump(
        imputer,
        imputer_path,
    )

    # Record the exact training-derived imputation statistics.
    imputation_statistics = {
        column: float(statistic)
        for column, statistic in zip(
            ONLINE_FEATURE_COLUMNS,
            imputer.statistics_,
        )
    }

    artifact_metadata = {
        "model_type": (
            "sklearn.linear_model.LogisticRegression"
        ),
        "model_version": "online-logistic-v1",
        "feature_columns": list(
            ONLINE_FEATURE_COLUMNS
        ),
        "num_features": len(
            ONLINE_FEATURE_COLUMNS
        ),
        "class_weight": "balanced",
        "random_state": 42,
        "max_iter": 3000,
        "training_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "training_patients": int(
            train["patient_id"].nunique()
        ),
        "validation_patients": int(
            validation["patient_id"].nunique()
        ),
        "imputation": {
            "method": "median",
            "fit_split": "train",
            "artifact": "imputer.joblib",
            "statistics": imputation_statistics,
        },
        "threshold_selection": "validation_max_f1",
        "threshold": float(
            threshold_result.threshold
        ),
        "validation_metrics": metrics,
        "source_preprocessing_version": metadata.get(
            "preprocessing_version"
        ),
    }

    metadata_path.write_text(
        json.dumps(
            artifact_metadata,
            indent=2,
        ),
        encoding="utf-8",
    )

    return artifact_metadata


def main() -> None:
    data_root = Path(
        "ai/data/processed_online"
    )

    artifact_root = Path(
        "ai/artifacts/online-logistic-v1"
    )

    metadata = train_online_logistic(
        data_root,
        artifact_root,
    )

    print(
        json.dumps(
            metadata,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()


