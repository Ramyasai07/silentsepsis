#!/usr/bin/env python3
"""Build patient-aware trend and deterioration features for the processed PhysioNet data."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "ai" / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sepsis_ai.features.trend_features import (  # noqa: E402
    build_feature_table,
    load_processed_split_data,
    load_split_manifest,
    validate_split_manifest,
)

PROCESSED_ROOT = REPO_ROOT / "ai" / "data" / "processed"
SPLIT_MANIFEST_PATH = (
    REPO_ROOT / "ai" / "data" / "splits" / "patient_split_manifest.csv"
)
OUTPUT_PATH = PROCESSED_ROOT / "engineered_patient_features.csv"


def _summarize_features(feature_table: pd.DataFrame) -> dict:
    engineered_columns = [
        col
        for col in feature_table.columns
        if any(
            suffix in col
            for suffix in [
                "_baseline",
                "_deviation",
                "_pct_deviation",
                "_delta",
                "_rolling_mean",
                "_rolling_std",
                "shock_index",
            ]
        )
    ]
    nan_fraction = (
        feature_table[engineered_columns].isna().mean().mean()
        if engineered_columns
        else 0.0
    )
    inf_fraction = (
        np.isinf(feature_table[engineered_columns].select_dtypes(include=["number"]))
        .mean()
        .mean()
        if engineered_columns
        else 0.0
    )
    original_columns = [
        col
        for col in feature_table.columns
        if col not in {"patient_id", "split", "ICULOS", "target"}
        and not any(
            suffix in col
            for suffix in [
                "_baseline",
                "_deviation",
                "_pct_deviation",
                "_delta",
                "_rolling_mean",
                "_rolling_std",
                "shock_index",
            ]
        )
    ]
    return {
        "input_rows": int(len(feature_table)),
        "original_features": int(len(original_columns)),
        "engineered_features": int(len(engineered_columns)),
        "final_feature_count": int(len(feature_table.columns)),
        "patient_count": int(feature_table["patient_id"].nunique()),
        "train_patients": int(
            feature_table.loc[feature_table["split"] == "train", "patient_id"].nunique()
        ),
        "validation_patients": int(
            feature_table.loc[
                feature_table["split"] == "validation", "patient_id"
            ].nunique()
        ),
        "test_patients": int(
            feature_table.loc[feature_table["split"] == "test", "patient_id"].nunique()
        ),
        "nan_fraction": float(nan_fraction),
        "inf_fraction": float(inf_fraction),
    }


def main() -> None:
    processed_df = load_processed_split_data(PROCESSED_ROOT)
    manifest = load_split_manifest(SPLIT_MANIFEST_PATH)
    validate_split_manifest(manifest, processed_df["patient_id"].dropna().unique())

    feature_table = build_feature_table(processed_df)
    if feature_table.empty:
        raise ValueError(
            "No processed patient rows were available for feature engineering."
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    feature_table.to_csv(OUTPUT_PATH, index=False)

    summary = _summarize_features(feature_table)
    print(f"Input row count: {summary['input_rows']}")
    print(f"Original feature count: {summary['original_features']}")
    print(f"Engineered features: {summary['engineered_features']}")
    print(f"Final feature count: {summary['final_feature_count']}")
    print(f"Patient count: {summary['patient_count']}")
    print(f"Train patients: {summary['train_patients']}")
    print(f"Validation patients: {summary['validation_patients']}")
    print(f"Test patients: {summary['test_patients']}")
    print(
        f"NaN/Inf fraction in engineered features: {summary['nan_fraction']:.6f} / {summary['inf_fraction']:.6f}"
    )
    print(f"Output path: {OUTPUT_PATH}")
    print("Sample engineered columns:")
    engineered_columns = [
        column
        for column in feature_table.columns
        if any(
            suffix in column
            for suffix in [
                "_baseline",
                "_deviation",
                "_pct_deviation",
                "_delta",
                "_rolling_mean",
                "_rolling_std",
                "shock_index",
            ]
        )
    ]
    print(engineered_columns[:10])


if __name__ == "__main__":
    main()
