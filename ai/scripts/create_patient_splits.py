#!/usr/bin/env python3
"""Create patient-level train/validation/test splits for the PhysioNet dataset.

This script reads the raw PSV files from training_setA and training_setB,
labels each patient/file as positive or negative based on SepsisLabel,
and writes a small split manifest under ai/data/splits/.

It does not preprocess the dataset or modify the raw files.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = REPO_ROOT / "ai" / "data" / "raw"
SPLIT_ROOT = REPO_ROOT / "ai" / "data" / "splits"
DATASET_NAMES = ["training_setA", "training_setB"]
RANDOM_SEED = 42


def find_psv_files(dataset_dir: Path) -> list[Path]:
    if not dataset_dir.exists():
        return []
    return sorted(path for path in dataset_dir.glob("*.psv") if path.is_file())


def patient_label_from_file(file_path: Path) -> bool:
    df = pd.read_csv(
        file_path,
        sep="|",
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )

    if "SepsisLabel" not in df.columns:
        raise ValueError(f"Missing SepsisLabel column in {file_path}")

    sepsis_values = pd.to_numeric(df["SepsisLabel"], errors="coerce")
    return bool((sepsis_values == 1).any())


def assign_split_counts(total: int) -> dict[str, int]:
    train_count = int(math.floor(total * 0.70))
    val_count = int(math.floor(total * 0.15))
    test_count = total - train_count - val_count

    if test_count < 0:
        test_count = 0

    return {
        "train": train_count,
        "validation": val_count,
        "test": test_count,
    }


def build_manifest() -> pd.DataFrame:
    rows: list[dict[str, str | bool]] = []

    for dataset_name in DATASET_NAMES:
        dataset_dir = RAW_ROOT / dataset_name
        for file_path in find_psv_files(dataset_dir):
            patient_id = file_path.stem
            patient_status = patient_label_from_file(file_path)

            rows.append(
                {
                    "patient_id": patient_id,
                    "training_set": dataset_name,
                    "patient_status": patient_status,
                    "file_path": str(file_path.relative_to(REPO_ROOT)),
                }
            )

    return pd.DataFrame(rows)


def stratified_split(manifest: pd.DataFrame) -> pd.DataFrame:
    rng = random.Random(RANDOM_SEED)
    grouped: dict[tuple[str, bool], list[int]] = defaultdict(list)

    for index in manifest.index:
        key = (manifest.loc[index, "training_set"], bool(manifest.loc[index, "patient_status"]))
        grouped[key].append(index)

    split_manifest = []

    for key, indices in grouped.items():
        rng.shuffle(indices)
        total = len(indices)
        counts = assign_split_counts(total)

        split_labels = ["train"] * counts["train"] + ["validation"] * counts["validation"] + ["test"] * counts["test"]
        if len(split_labels) != total:
            remaining = total - len(split_labels)
            split_labels.extend(["test"] * remaining)

        for index, split_name in zip(indices, split_labels):
            item = manifest.loc[index].copy()
            item["split"] = split_name
            split_manifest.append(item.to_dict())

    result = pd.DataFrame(split_manifest)
    return result[["patient_id", "training_set", "split", "patient_status", "file_path"]]


def verify_manifest(manifest: pd.DataFrame, expected_total: int) -> None:
    total_files = len(manifest)
    if total_files != expected_total:
        raise ValueError(f"Split count mismatch: expected {expected_total}, found {total_files}")

    duplicates = manifest[manifest.duplicated(subset=["patient_id"], keep=False)]
    if not duplicates.empty:
        raise ValueError(f"Duplicate patient IDs found across splits: {duplicates['patient_id'].tolist()}")

    all_expected = set()
    for dataset_name in DATASET_NAMES:
        for file_path in find_psv_files(REPO_ROOT / "ai" / "data" / "raw" / dataset_name):
            all_expected.add(file_path.stem)

    manifest_ids = set(manifest["patient_id"])
    missing = sorted(all_expected - manifest_ids)
    if missing:
        raise ValueError(f"Missing patient IDs from manifest: {missing[:10]}")


def print_split_summary(manifest: pd.DataFrame) -> None:
    print("Final split summary")
    print(f"Total files: {len(manifest)}")
    print(f"Train files: {(manifest['split'] == 'train').sum()}")
    print(f"Validation files: {(manifest['split'] == 'validation').sum()}")
    print(f"Test files: {(manifest['split'] == 'test').sum()}")

    for split_name in ["train", "validation", "test"]:
        subset = manifest[manifest["split"] == split_name]
        print(f"\n{split_name} split:")
        print(f"  positive patients: {(subset['patient_status'] == True).sum()}")
        print(f"  negative patients: {(subset['patient_status'] == False).sum()}")
        print(f"  training_setA: {(subset['training_set'] == 'training_setA').sum()}")
        print(f"  training_setB: {(subset['training_set'] == 'training_setB').sum()}")

    print("\nVerification checks:")
    print(f"- total split count = {len(manifest)}")
    print(f"- unique patient IDs = {manifest['patient_id'].nunique()}")
    print(f"- missing IDs from manifest = 0")


def main() -> None:
    print("Creating patient-level train/validation/test splits")
    print(f"Data root: {RAW_ROOT}")

    manifest = build_manifest()
    split_manifest = stratified_split(manifest)

    SPLIT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = SPLIT_ROOT / "patient_split_manifest.csv"
    split_manifest.to_csv(manifest_path, index=False)

    expected_total = 40_336
    verify_manifest(split_manifest, expected_total)
    print(f"Manifest written to: {manifest_path}")
    print_split_summary(split_manifest)
    print("\nFINAL SUMMARY: PASS")


if __name__ == "__main__":
    main()
