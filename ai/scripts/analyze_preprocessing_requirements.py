#!/usr/bin/env python3
"""Read-only preprocessing analysis for the PhysioNet Challenge 2019 dataset.

This script inspects the raw PSV files and the patient split manifest to assess
missing-value patterns, feature usability, and train/validation/test differences
without modifying the raw dataset or creating processed outputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = REPO_ROOT / "ai" / "data" / "raw"
SPLIT_MANIFEST = REPO_ROOT / "ai" / "data" / "splits" / "patient_split_manifest.csv"
DATASET_NAMES = ["training_setA", "training_setB"]


def get_split_manifest() -> pd.DataFrame:
    if not SPLIT_MANIFEST.exists():
        raise FileNotFoundError(f"Split manifest not found: {SPLIT_MANIFEST}")
    return pd.read_csv(SPLIT_MANIFEST)


def find_psv_files(dataset_dir: Path) -> list[Path]:
    if not dataset_dir.exists():
        return []
    return sorted(path for path in dataset_dir.glob("*.psv") if path.is_file())


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.strip(), errors="coerce")


def is_missing_value(value: object) -> bool:
    if value is None:
        return True

    text = str(value).strip()
    if text == "":
        return True

    if text.lower() in {"nan", "n/a", "na", "null", "none"}:
        return True

    return False


def read_patient_file(file_path: Path) -> pd.DataFrame:
    return pd.read_csv(
        file_path,
        sep="|",
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )


def summarize_split(split_name: str, manifest: pd.DataFrame) -> dict:
    split_rows = manifest[manifest["split"] == split_name].copy()
    split_rows = split_rows.reset_index(drop=True)

    file_stats: List[dict] = []
    feature_missing_total: Dict[str, int] = {}
    feature_total_count: Dict[str, int] = {}
    feature_values: Dict[str, list] = {}
    column_names: List[str] = []
    column_mismatches: List[str] = []
    unreadable_files: List[str] = []
    temporal_notes: List[str] = []
    rows_per_patient: List[int] = []
    valid_feature_count: Dict[str, int] = {}

    if split_rows.empty:
        return {
            "split_name": split_name,
            "file_count": 0,
            "row_count": 0,
            "rows_per_patient": [],
            "feature_missing_total": {},
            "feature_total_count": {},
            "feature_values": {},
            "column_names": [],
            "column_mismatches": [],
            "unreadable_files": [],
            "temporal_notes": [],
            "feature_usability": {},
            "numeric_summary": {},
            "categorical_columns": [],
            "constant_or_near_constant": [],
            "train_split_only": split_name == "train",
        }

    for _, row in split_rows.iterrows():
        file_path = REPO_ROOT / row["file_path"]
        patient_id = row["patient_id"]
        dataset_name = row["training_set"]

        try:
            df = read_patient_file(file_path)
        except Exception as exc:
            unreadable_files.append(f"{dataset_name}/{patient_id}: {exc}")
            continue

        if df.empty:
            unreadable_files.append(f"{dataset_name}/{patient_id}: empty file")
            continue

        rows_per_patient.append(len(df))

        if not column_names:
            column_names = list(df.columns)
        elif list(df.columns) != column_names:
            column_mismatches.append(
                f"{dataset_name}/{patient_id}: expected {column_names}, found {list(df.columns)}"
            )

        for col in df.columns:
            series = df[col]
            missing_count = int(series.map(is_missing_value).sum())
            feature_missing_total[col] = (
                feature_missing_total.get(col, 0) + missing_count
            )
            feature_total_count[col] = feature_total_count.get(col, 0) + len(series)

            numeric_series = safe_numeric(series)
            valid_numeric = numeric_series.dropna()
            if len(valid_numeric) > 0:
                feature_values.setdefault(col, []).extend(
                    valid_numeric.astype(float).tolist()
                )
                valid_feature_count[col] = valid_feature_count.get(col, 0) + len(
                    valid_numeric
                )

        file_stats.append(
            {
                "patient_id": patient_id,
                "dataset": dataset_name,
                "rows": len(df),
                "columns": list(df.columns),
            }
        )

        if len(df.columns) > 1:
            temporal_notes.append(
                f"{dataset_name}/{patient_id}: {len(df)} rows, {len(df.columns)} columns, has time-series structure"
            )

    feature_usability: Dict[str, dict] = {}
    for col in column_names:
        total = feature_total_count.get(col, 0)
        missing = feature_missing_total.get(col, 0)
        observed = total - missing
        observed_pct = (observed / total * 100) if total else 0.0
        feature_usability[col] = {
            "total_rows": total,
            "missing": missing,
            "missing_pct": (missing / total * 100) if total else 0.0,
            "observed": observed,
            "observed_pct": observed_pct,
            "usable_if_observed_pct_gt_0": observed_pct > 0,
        }

    numeric_summary: Dict[str, dict] = {}
    for col, values in feature_values.items():
        if not values:
            continue
        series = pd.Series(values)
        numeric_summary[col] = {
            "min": float(series.min()),
            "max": float(series.max()),
            "mean": float(series.mean()),
            "median": float(series.median()),
            "std": float(series.std(ddof=1)) if len(series) > 1 else 0.0,
        }

    categorical_columns = []
    for col in column_names:
        if col not in numeric_summary:
            categorical_columns.append(col)

    constant_or_near_constant = []
    for col, values in feature_values.items():
        series = pd.Series(values)
        if series.nunique() <= 1:
            constant_or_near_constant.append(col)
        elif len(series) > 0:
            unique_ratio = series.nunique() / len(series)
            if unique_ratio < 0.01:
                constant_or_near_constant.append(col)

    summary = {
        "split_name": split_name,
        "file_count": len(split_rows),
        "row_count": sum(rows_per_patient),
        "rows_per_patient": rows_per_patient,
        "feature_missing_total": feature_missing_total,
        "feature_total_count": feature_total_count,
        "column_names": column_names,
        "column_mismatches": column_mismatches,
        "unreadable_files": unreadable_files,
        "temporal_notes": temporal_notes,
        "feature_usability": feature_usability,
        "numeric_summary": numeric_summary,
        "categorical_columns": categorical_columns,
        "constant_or_near_constant": constant_or_near_constant,
    }
    return summary


def print_section(title: str) -> None:
    print(f"\n{'=' * 80}")
    print(title)
    print(f"{'=' * 80}")


def print_split_summary(split_name: str, summary: dict) -> None:
    print_section(f"{split_name.upper()} analysis")
    print(f"Files in split: {summary['file_count']}")
    print(f"Total rows across files: {summary['row_count']}")
    print(
        f"Rows per patient/file: min={min(summary['rows_per_patient']) if summary['rows_per_patient'] else 0}, max={max(summary['rows_per_patient']) if summary['rows_per_patient'] else 0}, mean={sum(summary['rows_per_patient']) / len(summary['rows_per_patient']) if summary['rows_per_patient'] else 0:.2f}, median={pd.Series(summary['rows_per_patient']).median() if summary['rows_per_patient'] else 0}"
    )
    print(f"Column names/order: {summary['column_names']}")
    print(f"Column count: {len(summary['column_names'])}")

    print("\nMissingness by feature:")
    for col in summary["column_names"]:
        total = summary["feature_total_count"].get(col, 0)
        missing = summary["feature_missing_total"].get(col, 0)
        pct = (missing / total * 100) if total else 0.0
        print(f"- {col}: missing={missing}, missing_pct={pct:.2f}%")

    print("\nFeature usability check:")
    for col, info in summary["feature_usability"].items():
        print(
            f"- {col}: observed={info['observed']}, observed_pct={info['observed_pct']:.2f}%, "
            f"missing_pct={info['missing_pct']:.2f}%"
        )

    if summary["numeric_summary"]:
        print("\nNumeric summary (train split only would be the main basis for stats):")
        for col, stats in summary["numeric_summary"].items():
            print(
                f"- {col}: min={stats['min']}, max={stats['max']}, mean={stats['mean']:.2f}, "
                f"median={stats['median']}, std={stats['std']:.2f}"
            )

    if summary["categorical_columns"]:
        print("\nCategorical / non-numeric columns:")
        for col in summary["categorical_columns"]:
            print(f"- {col}")

    if summary["constant_or_near_constant"]:
        print("\nConstant or near-constant features:")
        for col in summary["constant_or_near_constant"]:
            print(f"- {col}")

    if summary["unreadable_files"]:
        print("\nUnreadable or empty files:")
        for item in summary["unreadable_files"]:
            print(f"- {item}")

    if summary["column_mismatches"]:
        print("\nColumn mismatches across files:")
        for item in summary["column_mismatches"]:
            print(f"- {item}")

    if summary["temporal_notes"]:
        print("\nTemporal structure observations:")
        for item in summary["temporal_notes"][:5]:
            print(f"- {item}")


def print_recommendations() -> None:
    print_section("Recommended preprocessing considerations")
    print(
        "- Missing-value handling must be decided based on the observed patterns and clinical meaning of each feature."
    )
    print(
        "- Imputation or masking strategies may be needed for features with substantial missingness."
    )
    print(
        "- Scaling/normalization may be needed for continuous features, especially if using numerical models."
    )
    print(
        "- Sequence length handling should be planned carefully because each patient file is a time series with varying row counts."
    )
    print(
        "- Features with a very high missing rate or near-zero variability may need review or removal."
    )
    print(
        "- Temporal structure should be preserved if the downstream task uses sequence-aware methods."
    )
    print(
        "- Non-numeric or constant features should be reviewed before any modeling pipeline is designed."
    )
    print(
        "- This script intentionally does not choose an automatic preprocessing strategy."
    )


def main() -> None:
    print("PhysioNet preprocessing analysis")
    print(f"Data root: {RAW_ROOT}")

    manifest = get_split_manifest()
    split_names = ["train", "validation", "test"]

    for split_name in split_names:
        summary = summarize_split(split_name, manifest)
        print_split_summary(split_name, summary)

    print_recommendations()
    print("\nFINAL SUMMARY: ANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
