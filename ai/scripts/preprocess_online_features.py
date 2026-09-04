#!/usr/bin/env python3
"""Build stateless online-compatible feature files from raw PhysioNet rows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from ai.ml.online_preprocessing import (
    load_split_manifest,
    online_metadata,
    transform_online_frame,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_ROOT = REPO_ROOT / "ai" / "data" / "raw"
DEFAULT_MANIFEST = REPO_ROOT / "ai" / "data" / "splits" / "patient_split_manifest.csv"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "ai" / "data" / "online_processed"


def read_raw_patient(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path, sep="|", dtype=str, keep_default_na=False, low_memory=False
    )


def build_online_dataset(
    raw_root: Path, manifest_path: Path, output_root: Path
) -> None:
    manifest = load_split_manifest(manifest_path)
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(
            f"Output directory must be empty before generation: {output_root}"
        )
    output_root.mkdir(parents=True, exist_ok=True)
    handles: dict[str, bool] = {}
    for split_name in ("train", "validation", "test"):
        output_path = output_root / f"{split_name}.csv"
        if output_path.exists():
            output_path.unlink()
        handles[split_name] = False

    for record in manifest.itertuples(index=False):
        manifest_file = Path(record.file_path)
        raw_path = (
            manifest_file if manifest_file.is_absolute() else REPO_ROOT / manifest_file
        )
        if not raw_path.exists():
            raw_path = raw_root / record.training_set / f"{record.patient_id}.psv"
        raw_frame = read_raw_patient(raw_path)
        transformed = transform_online_frame(raw_frame)
        transformed.insert(0, "patient_id", str(record.patient_id))
        if "SepsisLabel" in raw_frame:
            transformed["target"] = (
                pd.to_numeric(raw_frame["SepsisLabel"], errors="coerce")
                .fillna(0)
                .astype(int)
            )
        output_path = output_root / f"{record.split}.csv"
        transformed.to_csv(
            output_path, mode="a", header=not handles[record.split], index=False
        )
        handles[record.split] = True

    (output_root / "preprocessing_metadata.json").write_text(
        json.dumps(online_metadata(), indent=2),
        encoding="utf-8",
    )


def validate_online_dataset(output_root: Path, manifest_path: Path) -> None:
    manifest = load_split_manifest(manifest_path)
    contract = online_metadata()
    expected_columns = ["patient_id", *contract["feature_columns"], "target"]
    expected_rows = {split: 0 for split in ("train", "validation", "test")}
    expected_patients = {split: set() for split in ("train", "validation", "test")}

    for record in manifest.itertuples(index=False):
        raw_frame = read_raw_patient(REPO_ROOT / Path(record.file_path))
        expected_rows[record.split] += len(raw_frame)
        expected_patients[record.split].add(str(record.patient_id))

    metadata_path = output_root / "preprocessing_metadata.json"
    if not metadata_path.exists():
        raise ValueError("Online preprocessing metadata was not written")
    written_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if written_metadata["feature_columns"] != contract["feature_columns"]:
        raise ValueError(
            "Written online metadata feature order does not match the contract"
        )

    actual_patients = {}
    for split_name in ("train", "validation", "test"):
        frame = pd.read_csv(output_root / f"{split_name}.csv")
        if list(frame.columns) != expected_columns:
            raise ValueError(
                f"{split_name}: output columns do not match online metadata"
            )
        if len(frame) != expected_rows[split_name]:
            raise ValueError(
                f"{split_name}: output row count does not match raw source rows"
            )
        if frame["patient_id"].isna().any():
            raise ValueError(f"{split_name}: patient_id contains null values")
        if frame["target"].isna().any() or not set(frame["target"].unique()).issubset(
            {0, 1}
        ):
            raise ValueError(f"{split_name}: target must be binary and non-null")
        actual_patients[split_name] = set(frame["patient_id"].astype(str))
        if actual_patients[split_name] != expected_patients[split_name]:
            raise ValueError(f"{split_name}: patient IDs do not match the manifest")

    for first, second in (
        ("train", "validation"),
        ("train", "test"),
        ("validation", "test"),
    ):
        if actual_patients[first] & actual_patients[second]:
            raise ValueError(f"Patient leakage detected between {first} and {second}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    build_online_dataset(args.raw_root, args.manifest, args.output_root)
    validate_online_dataset(args.output_root, args.manifest)


if __name__ == "__main__":
    main()
