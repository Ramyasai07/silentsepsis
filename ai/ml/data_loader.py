"""Load and validate the processed PhysioNet split files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

SPLIT_NAMES = ("train", "validation", "test")


@dataclass(frozen=True)
class ProcessedSplit:
    features: pd.DataFrame
    target: pd.Series
    patient_ids: pd.Series


@dataclass(frozen=True)
class ProcessedDataset:
    splits: dict[str, ProcessedSplit]
    feature_columns: tuple[str, ...]
    metadata: dict[str, object]


def load_processed_dataset(
    data_root: Path,
    split_names: tuple[str, ...] = SPLIT_NAMES,
) -> ProcessedDataset:
    metadata_path = data_root / "preprocessing_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Preprocessing metadata not found: {metadata_path}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    feature_columns = tuple(metadata.get("feature_columns", []))
    if len(feature_columns) != metadata.get("num_features"):
        raise ValueError("Metadata feature_columns does not match num_features")
    if len(set(feature_columns)) != len(feature_columns):
        raise ValueError("Metadata contains duplicate feature columns")

    unknown_splits = set(split_names) - set(SPLIT_NAMES)
    if unknown_splits:
        raise ValueError(f"Unknown processed splits: {sorted(unknown_splits)}")

    splits: dict[str, ProcessedSplit] = {}
    expected_columns = ["patient_id", *feature_columns, "target"]
    for split_name in split_names:
        path = data_root / f"{split_name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Processed split not found: {path}")

        frame = pd.read_csv(path)
        if list(frame.columns) != expected_columns:
            raise ValueError(
                f"{split_name}: columns do not match preprocessing metadata"
            )
        if frame["patient_id"].isna().any():
            raise ValueError(f"{split_name}: patient_id must be present")
        if frame["target"].isna().any() or not set(frame["target"].unique()).issubset(
            {0, 1}
        ):
            raise ValueError(f"{split_name}: target must contain only 0 and 1")
        if frame[list(feature_columns)].isna().any().any():
            raise ValueError(f"{split_name}: feature values contain NaN")

        splits[split_name] = ProcessedSplit(
            features=frame.loc[:, feature_columns].astype(np.float32),
            target=frame["target"].astype(np.int8),
            patient_ids=frame["patient_id"].astype(str),
        )

    patient_sets = {name: set(split.patient_ids) for name, split in splits.items()}
    for first, second in combinations(split_names, 2):
        if patient_sets[first] & patient_sets[second]:
            raise ValueError(f"Patient leakage detected between {first} and {second}")

    return ProcessedDataset(
        splits=splits,
        feature_columns=feature_columns,
        metadata=metadata,
    )
