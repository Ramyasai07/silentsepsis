#!/usr/bin/env python3
"""Read-only profiling for the PhysioNet Challenge 2019 training dataset.

This script inspects the PSV files in:
- ai/data/raw/training_setA
- ai/data/raw/training_setB

It reports file counts, row counts, feature columns, missing values,
summary statistics, and SepsisLabel distribution without modifying the dataset.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = REPO_ROOT / "ai" / "data" / "raw"
DATASET_NAMES = ["training_setA", "training_setB"]


def find_psv_files(dataset_dir: Path) -> list[Path]:
    if not dataset_dir.exists():
        return []
    return sorted(path for path in dataset_dir.glob("*.psv") if path.is_file())


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.strip(), errors="coerce")


def profile_training_set(dataset_name: str) -> dict:
    dataset_dir = RAW_ROOT / dataset_name
    files = find_psv_files(dataset_dir)

    total_rows = 0
    rows_per_file: list[int] = []
    unreadable_files: list[str] = []
    feature_missing: dict[str, int] = defaultdict(int)
    feature_total: dict[str, int] = defaultdict(int)
    feature_numeric_values: dict[str, list[float]] = defaultdict(list)
    sepsis_zero = 0
    sepsis_one = 0
    patients_with_sepsis_one = 0
    column_names: list[str] | None = None
    column_name_mismatches: list[str] = []

    for file_path in files:
        rel_path = str(file_path.relative_to(REPO_ROOT))

        try:
            df = pd.read_csv(
                file_path,
                sep="|",
                dtype=str,
                keep_default_na=False,
                low_memory=False,
            )
        except Exception as exc:
            unreadable_files.append(f"{rel_path}: {exc}")
            continue

        if df.empty:
            unreadable_files.append(f"{rel_path}: empty file")
            continue

        if column_names is None:
            column_names = list(df.columns)
        elif list(df.columns) != column_names:
            column_name_mismatches.append(
                f"{rel_path}: expected {column_names}, found {list(df.columns)}"
            )

        rows_per_file.append(len(df))
        total_rows += len(df)

        for col in df.columns:
            series = df[col]
            feature_total[col] += len(series)
            missing_count = int(series.astype(str).str.strip().eq("").sum())
            feature_missing[col] += missing_count

            numeric_values = safe_numeric(series)
            valid_numeric = numeric_values.dropna()
            feature_numeric_values[col].extend(valid_numeric.astype(float).tolist())

        if "SepsisLabel" in df.columns:
            sepsis_series = safe_numeric(df["SepsisLabel"])
            sepsis_zero += int((sepsis_series == 0).sum())
            sepsis_one += int((sepsis_series == 1).sum())
            if (sepsis_series == 1).any():
                patients_with_sepsis_one += 1

    ordered_columns = column_names if column_names is not None else []
    feature_stats: dict[str, dict[str, float | int]] = {}

    for col in ordered_columns:
        values = feature_numeric_values.get(col, [])
        if not values:
            continue

        series = pd.Series(values)
        feature_stats[col] = {
            "min": float(series.min()),
            "max": float(series.max()),
            "mean": float(series.mean()),
            "median": float(series.median()),
        }

    return {
        "dataset_name": dataset_name,
        "file_count": len(files),
        "row_count": total_rows,
        "rows_per_file": rows_per_file,
        "ordered_columns": ordered_columns,
        "column_count": len(ordered_columns),
        "feature_missing": dict(feature_missing),
        "feature_total": dict(feature_total),
        "feature_stats": feature_stats,
        "sepsis_zero": sepsis_zero,
        "sepsis_one": sepsis_one,
        "patients_with_sepsis_one": patients_with_sepsis_one,
        "unreadable_files": unreadable_files,
        "column_name_mismatches": column_name_mismatches,
    }


def print_section(title: str) -> None:
    print(f"\n{'=' * 80}")
    print(title)
    print(f"{'=' * 80}")


def print_profile(profile: dict) -> None:
    dataset_name = profile["dataset_name"]
    print_section(f"Dataset: {dataset_name}")
    print(f"PSV files: {profile['file_count']}")
    print(f"Total rows: {profile['row_count']}")
    print(f"Files with at least one SepsisLabel=1: {profile['patients_with_sepsis_one']}")
    print(f"SepsisLabel distribution: 0={profile['sepsis_zero']}, 1={profile['sepsis_one']}")
    if profile["sepsis_zero"] + profile["sepsis_one"] > 0:
        total_labels = profile["sepsis_zero"] + profile["sepsis_one"]
        print(
            "SepsisLabel percentage: "
            f"0={profile['sepsis_zero'] / total_labels * 100:.2f}%, "
            f"1={profile['sepsis_one'] / total_labels * 100:.2f}%"
        )

    print(f"Column order: {profile['ordered_columns']}")
    print(f"Number of columns: {profile['column_count']}")

    if profile["rows_per_file"]:
        print(f"Rows per file: min={min(profile['rows_per_file'])}, max={max(profile['rows_per_file'])}, mean={sum(profile['rows_per_file']) / len(profile['rows_per_file']):.2f}, median={pd.Series(profile['rows_per_file']).median()}")

    print("\nMissing value summary by feature:")
    for col in profile["ordered_columns"]:
        total_rows = profile["feature_total"].get(col, 0)
        missing = profile["feature_missing"].get(col, 0)
        if total_rows == 0:
            pct = 0.0
        else:
            pct = (missing / total_rows) * 100
        print(f"- {col}: missing={missing}, pct={pct:.2f}%")

    print("\nNumeric summary by feature:")
    for col, stats in profile["feature_stats"].items():
        print(
            f"- {col}: min={stats['min']}, max={stats['max']}, "
            f"mean={stats['mean']}, median={stats['median']}"
        )

    if profile["unreadable_files"]:
        print("\nUnreadable files:")
        for item in profile["unreadable_files"]:
            print(f"- {item}")

    if profile["column_name_mismatches"]:
        print("\nColumn name mismatches:")
        for item in profile["column_name_mismatches"]:
            print(f"- {item}")


def main() -> None:
    print("PhysioNet Challenge 2019 training dataset profiling")
    print(f"Data root: {RAW_ROOT}")

    dataset_profiles = []
    total_file_count = 0
    total_rows = 0
    total_sepsis_zero = 0
    total_sepsis_one = 0
    patients_with_sepsis_one = 0

    for dataset_name in DATASET_NAMES:
        profile = profile_training_set(dataset_name)
        dataset_profiles.append(profile)
        total_file_count += profile["file_count"]
        total_rows += profile["row_count"]
        total_sepsis_zero += profile["sepsis_zero"]
        total_sepsis_one += profile["sepsis_one"]
        patients_with_sepsis_one += profile["patients_with_sepsis_one"]
        print_profile(profile)

    print_section("Final Summary")
    print(f"Training_setA files: {dataset_profiles[0]['file_count']}")
    print(f"Training_setB files: {dataset_profiles[1]['file_count']}")
    print(f"Total files: {total_file_count}")
    print(f"Total rows across all files: {total_rows}")
    print(f"Total SepsisLabel=0: {total_sepsis_zero}")
    print(f"Total SepsisLabel=1: {total_sepsis_one}")
    if total_sepsis_zero + total_sepsis_one > 0:
        print(
            "SepsisLabel percentage: "
            f"0={(total_sepsis_zero / (total_sepsis_zero + total_sepsis_one)) * 100:.2f}%, "
            f"1={(total_sepsis_one / (total_sepsis_zero + total_sepsis_one)) * 100:.2f}%"
        )
    print(f"Files containing at least one SepsisLabel=1: {patients_with_sepsis_one}")
    print("Summary complete. No dataset files were read, modified, moved, or rewritten.")


if __name__ == "__main__":
    main()
