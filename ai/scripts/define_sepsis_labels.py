#!/usr/bin/env python3
"""Define the early sepsis prediction target using the official PhysioNet labeling.

Important: the PhysioNet Challenge 2019 dataset already defines SepsisLabel as 1
starting 6 hours before the clinical sepsis onset. This means the dataset's
SepsisLabel already encodes the early-warning target window.

For each patient, we therefore use the existing SepsisLabel as the target
without applying an additional 6-hour shift. Rows before the first SepsisLabel=1
are labeled 0, and rows from the first SepsisLabel=1 onward are labeled 1.

This script is read-only. It does not modify the raw PSV files or the split
manifest. It only inspects the patient files and counts label assignments for
train, validation, and test.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = REPO_ROOT / "ai" / "data" / "raw"
SPLIT_MANIFEST = REPO_ROOT / "ai" / "data" / "splits" / "patient_split_manifest.csv"
SPLIT_NAMES = ["train", "validation", "test"]


def load_split_manifest() -> pd.DataFrame:
    if not SPLIT_MANIFEST.exists():
        raise FileNotFoundError(f"Split manifest not found: {SPLIT_MANIFEST}")

    manifest = pd.read_csv(SPLIT_MANIFEST)
    valid_splits = set(SPLIT_NAMES)
    bad_splits = set(manifest["split"]) - valid_splits
    if bad_splits:
        raise ValueError(f"Unexpected split values found: {sorted(bad_splits)}")
    return manifest


def read_patient_file(file_path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        file_path,
        sep="|",
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )
    return df


def build_patient_labels(patient_df: pd.DataFrame) -> list[dict]:
    required_cols = {"ICULOS", "SepsisLabel"}
    missing_cols = required_cols - set(patient_df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {sorted(missing_cols)}")

    patient_df = patient_df.copy()
    patient_df["ICULOS"] = pd.to_numeric(patient_df["ICULOS"], errors="coerce")
    patient_df["SepsisLabel"] = pd.to_numeric(patient_df["SepsisLabel"], errors="coerce")

    patient_df = patient_df.sort_values("ICULOS", kind="mergesort").reset_index(drop=True)
    patient_df = patient_df[patient_df["ICULOS"].notna()].copy()

    patient_labels: list[dict] = []
    first_positive_time = None
    for _, row in patient_df.iterrows():
        if pd.notna(row["SepsisLabel"]) and row["SepsisLabel"] == 1:
            first_positive_time = float(row["ICULOS"])
            break

    if first_positive_time is None:
        for row_index, row in patient_df.iterrows():
            patient_labels.append(
                {
                    "row_index": int(row_index),
                    "ICULOS": float(row["ICULOS"]),
                    "label": 0,
                }
            )
        return patient_labels

    for row_index, row in patient_df.iterrows():
        current_time = float(row["ICULOS"])
        if current_time < first_positive_time:
            label = 0
        else:
            label = 1

        patient_labels.append(
            {
                "row_index": int(row_index),
                "ICULOS": current_time,
                "label": int(label),
            }
        )

    patient_labels.sort(key=lambda item: item["ICULOS"])
    return patient_labels


def summarize_split(split_name: str, manifest: pd.DataFrame) -> dict:
    split_rows = manifest[manifest["split"] == split_name].reset_index(drop=True)
    total_labels = 0
    positive_labels = 0
    negative_labels = 0

    for _, row in split_rows.iterrows():
        patient_id = row["patient_id"]
        file_path = REPO_ROOT / row["file_path"]

        if not file_path.exists():
            raise FileNotFoundError(f"Missing patient file for {patient_id}: {file_path}")

        patient_df = read_patient_file(file_path)
        labels = build_patient_labels(patient_df)

        total_labels += len(labels)
        positive_labels += sum(1 for item in labels if item["label"] == 1)
        negative_labels += sum(1 for item in labels if item["label"] == 0)

    return {
        "split_name": split_name,
        "total_labels": total_labels,
        "positive_labels": positive_labels,
        "negative_labels": negative_labels,
    }


def main() -> None:
    print("Early sepsis prediction label definition")
    print("Target: use the official PhysioNet SepsisLabel semantics directly.")
    print("PhysioNet already labels the 6-hour pre-onset warning window with SepsisLabel=1.")
    print(f"Data root: {RAW_ROOT}")
    print(f"Split manifest: {SPLIT_MANIFEST}\n")

    manifest = load_split_manifest()
    split_summary: dict[str, dict] = {}

    for split_name in SPLIT_NAMES:
        summary = summarize_split(split_name, manifest)
        split_summary[split_name] = summary
        print(f"{split_name.upper()} split:")
        print(f"  created labels: {summary['total_labels']}")
        print(f"  positive labels (1): {summary['positive_labels']}")
        print(f"  negative labels (0): {summary['negative_labels']}")
        print()

    total_created = sum(summary["total_labels"] for summary in split_summary.values())
    total_positive = sum(summary["positive_labels"] for summary in split_summary.values())
    total_negative = sum(summary["negative_labels"] for summary in split_summary.values())

    print("FINAL SUMMARY")
    print(f"Total labeled rows created: {total_created}")
    print(f"Total positive labels: {total_positive}")
    print(f"Total negative labels: {total_negative}")
    print("No raw PSV files were modified; no split manifest was changed.")


if __name__ == "__main__":
    main()
