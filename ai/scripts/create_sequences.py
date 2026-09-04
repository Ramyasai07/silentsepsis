#!/usr/bin/env python3
"""Patient-aware sequence preparation for the SilentSepsis LSTM/GRU pipeline.

This stage reads the already-preprocessed split CSV files and creates fixed-length
sequence windows for each patient only. It does not train a model, does not modify
raw data, and does not alter the existing preprocessing outputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_ROOT = REPO_ROOT / "ai" / "data" / "processed"
SEQUENCE_ROOT = REPO_ROOT / "ai" / "data" / "sequences"
SPLIT_MANIFEST = REPO_ROOT / "ai" / "data" / "splits" / "patient_split_manifest.csv"
SPLIT_NAMES = ["train", "validation", "test"]
SEQUENCE_LENGTH = 12


def load_feature_names() -> list[str]:
    metadata_path = PROCESSED_ROOT / "preprocessing_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing preprocessing metadata: {metadata_path}")

    with metadata_path.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)

    if "feature_columns" in metadata:
        feature_names = metadata["feature_columns"]
    elif "feature_names" in metadata:
        feature_names = metadata["feature_names"]
    else:
        raise ValueError("preprocessing_metadata.json does not contain a feature list.")

    feature_names = [str(name) for name in feature_names]
    if not feature_names:
        raise ValueError("The feature list in preprocessing_metadata.json is empty.")

    return feature_names


def filter_input_feature_names(feature_names: list[str]) -> list[str]:
    protected = {"patient_id", "ICULOS", "target", "SepsisLabel"}
    filtered = [feature for feature in feature_names if feature not in protected]

    if not filtered:
        raise ValueError(
            "No valid LSTM input features remain after filtering protected columns."
        )

    for feature in filtered:
        if feature in protected:
            raise ValueError(
                f"Protected column remains in the LSTM feature list: {feature}"
            )

    return filtered


def verify_feature_names(feature_names: list[str]) -> None:
    protected = {"patient_id", "ICULOS", "target", "SepsisLabel"}
    remaining = [feature for feature in feature_names if feature not in protected]
    if not remaining:
        raise ValueError(
            "No valid LSTM input features remain after filtering protected columns."
        )
    if any(feature in protected for feature in remaining):
        raise ValueError(
            "Protected columns were not fully removed from the feature list."
        )
    return None


def load_manifest_split_map() -> tuple[dict[str, str], dict[str, set[str]], set[str]]:
    if not SPLIT_MANIFEST.exists():
        raise FileNotFoundError(f"Split manifest not found: {SPLIT_MANIFEST}")

    manifest = pd.read_csv(SPLIT_MANIFEST, usecols=["patient_id", "split"])
    patient_to_split: dict[str, str] = {}
    split_to_patients: dict[str, set[str]] = {
        split_name: set() for split_name in SPLIT_NAMES
    }

    for row in manifest.itertuples(index=False):
        patient_id = str(row.patient_id)
        split_name = str(row.split)
        if split_name not in SPLIT_NAMES:
            raise ValueError(f"Unexpected split name in manifest: {split_name}")
        if (
            patient_id in patient_to_split
            and patient_to_split[patient_id] != split_name
        ):
            raise ValueError(
                f"Patient {patient_id} appears in multiple splits in the manifest."
            )
        patient_to_split[patient_id] = split_name
        split_to_patients[split_name].add(patient_id)

    all_manifest_patient_ids = set(patient_to_split)
    return patient_to_split, split_to_patients, all_manifest_patient_ids


def iter_patient_blocks(split_name: str, feature_names: list[str]):
    input_path = PROCESSED_ROOT / f"{split_name}.csv"
    if not input_path.exists():
        raise FileNotFoundError(
            f"Missing processed CSV for split '{split_name}': {input_path}"
        )

    required_columns = ["patient_id", "ICULOS", "target", *feature_names]
    current_patient_id = None
    current_rows: list[tuple[object, ...]] = []

    for chunk in pd.read_csv(input_path, chunksize=100_000):
        missing_columns = [col for col in required_columns if col not in chunk.columns]
        if missing_columns:
            raise ValueError(
                f"{split_name}: missing required columns in processed data -> {missing_columns}"
            )

        chunk = chunk[required_columns].copy()
        chunk["patient_id"] = chunk["patient_id"].astype(str)
        chunk["ICULOS"] = pd.to_numeric(chunk["ICULOS"], errors="coerce")
        chunk["target"] = pd.to_numeric(chunk["target"], errors="coerce")

        for row in chunk.itertuples(index=False, name=None):
            patient_id = str(row[0])
            if current_patient_id is None:
                current_patient_id = patient_id
            if patient_id != current_patient_id:
                yield pd.DataFrame(
                    current_rows,
                    columns=["patient_id", "ICULOS", "target", *feature_names],
                )
                current_patient_id = patient_id
                current_rows = [row]
            else:
                current_rows.append(row)

    if current_rows:
        yield pd.DataFrame(
            current_rows, columns=["patient_id", "ICULOS", "target", *feature_names]
        )


def patient_sequence_counts(
    patient_df: pd.DataFrame, feature_names: list[str]
) -> tuple[int, int, int, int, int]:
    patient_df = patient_df.copy()
    patient_df = patient_df.sort_values("ICULOS", kind="mergesort").reset_index(
        drop=True
    )
    patient_df["ICULOS"] = pd.to_numeric(patient_df["ICULOS"], errors="coerce")
    patient_df["target"] = pd.to_numeric(patient_df["target"], errors="coerce")
    patient_df = patient_df.dropna(subset=["ICULOS", "target"]).reset_index(drop=True)

    if len(patient_df) < SEQUENCE_LENGTH:
        return 0, 0, 0, 0, 0

    valid_sequences = 0
    positive_sequences = 0
    negative_sequences = 0
    candidate_windows = 0
    skipped_windows = 0

    for start_index in range(len(patient_df) - SEQUENCE_LENGTH + 1):
        candidate_windows += 1
        window_df = patient_df.iloc[start_index : start_index + SEQUENCE_LENGTH].copy()
        icu_values = window_df["ICULOS"].to_numpy(dtype=np.float64)

        if not np.all(np.diff(icu_values) == 1.0):
            skipped_windows += 1
            continue

        x_values = window_df[feature_names].to_numpy(dtype=np.float64, copy=True)
        if np.isnan(x_values).any() or np.isinf(x_values).any():
            raise ValueError("Sequence contains NaN or infinite values.")

        target_value = int(window_df["target"].iloc[-1])
        if target_value not in {0, 1}:
            raise ValueError(f"Target value must be 0 or 1; got {target_value}.")

        valid_sequences += 1
        if target_value == 1:
            positive_sequences += 1
        else:
            negative_sequences += 1

    return (
        valid_sequences,
        positive_sequences,
        negative_sequences,
        candidate_windows,
        skipped_windows,
    )


def count_split_sequences(split_name: str, feature_names: list[str]) -> dict[str, int]:
    summary = {
        "candidate_windows": 0,
        "skipped_windows": 0,
        "sequences": 0,
        "positive": 0,
        "negative": 0,
    }

    for patient_block in iter_patient_blocks(split_name, feature_names):
        if patient_block.empty:
            continue
        sequences, positive, negative, candidate_windows, skipped_windows = (
            patient_sequence_counts(patient_block, feature_names)
        )
        summary["sequences"] += sequences
        summary["positive"] += positive
        summary["negative"] += negative
        summary["candidate_windows"] += candidate_windows
        summary["skipped_windows"] += skipped_windows

    return summary


def fill_split_sequences(
    split_name: str, feature_names: list[str], total_sequences: int
) -> dict[str, int]:
    num_features = len(feature_names)
    temp_x_path = SEQUENCE_ROOT / f".{split_name}_X.dat"
    temp_y_path = SEQUENCE_ROOT / f".{split_name}_y.dat"

    X_mem = np.memmap(
        temp_x_path,
        dtype=np.float64,
        mode="w+",
        shape=(total_sequences, SEQUENCE_LENGTH, num_features),
    )
    y_mem = np.memmap(temp_y_path, dtype=np.int64, mode="w+", shape=(total_sequences,))

    write_index = 0
    summary = {
        "candidate_windows": 0,
        "skipped_windows": 0,
        "sequences": 0,
        "positive": 0,
        "negative": 0,
    }

    for patient_block in iter_patient_blocks(split_name, feature_names):
        if patient_block.empty:
            continue

        patient_df = patient_block.copy()
        patient_df = patient_df.sort_values("ICULOS", kind="mergesort").reset_index(
            drop=True
        )
        patient_df["ICULOS"] = pd.to_numeric(patient_df["ICULOS"], errors="coerce")
        patient_df["target"] = pd.to_numeric(patient_df["target"], errors="coerce")
        patient_df = patient_df.dropna(subset=["ICULOS", "target"]).reset_index(
            drop=True
        )

        for start_index in range(len(patient_df) - SEQUENCE_LENGTH + 1):
            summary["candidate_windows"] += 1
            window_df = patient_df.iloc[
                start_index : start_index + SEQUENCE_LENGTH
            ].copy()
            icu_values = window_df["ICULOS"].to_numpy(dtype=np.float64)

            if not np.all(np.diff(icu_values) == 1.0):
                summary["skipped_windows"] += 1
                continue

            x_values = window_df[feature_names].to_numpy(dtype=np.float64, copy=True)
            if np.isnan(x_values).any() or np.isinf(x_values).any():
                raise ValueError(
                    f"{split_name}: sequence contains NaN or infinite values."
                )

            target_value = int(window_df["target"].iloc[-1])
            if target_value not in {0, 1}:
                raise ValueError(
                    f"{split_name}: target value must be 0 or 1; got {target_value}."
                )

            X_mem[write_index] = x_values
            y_mem[write_index] = target_value
            write_index += 1
            summary["sequences"] += 1
            if target_value == 1:
                summary["positive"] += 1
            else:
                summary["negative"] += 1

    validate_sequence_arrays(X_mem, y_mem, len(feature_names), split_name)
    X_mem.flush()
    y_mem.flush()

    if write_index != total_sequences:
        raise ValueError(
            f"{split_name}: expected {total_sequences} sequences, but wrote {write_index}."
        )

    output_path = SEQUENCE_ROOT / f"{split_name}_sequences.npz"
    np.savez_compressed(output_path, X=X_mem, y=y_mem)

    del X_mem
    del y_mem
    temp_x_path.unlink(missing_ok=True)
    temp_y_path.unlink(missing_ok=True)

    return summary


def validate_sequence_arrays(
    X: np.ndarray, y: np.ndarray, feature_count: int, split_name: str
) -> None:
    if X.shape[0] != y.shape[0]:
        raise ValueError(
            f"{split_name}: X and y sample counts do not match ({X.shape[0]} vs {y.shape[0]})"
        )
    if X.ndim != 3:
        raise ValueError(f"{split_name}: X must be 3D; got shape {X.shape}")
    if X.shape[1] != SEQUENCE_LENGTH:
        raise ValueError(
            f"{split_name}: expected sequence length {SEQUENCE_LENGTH}, got {X.shape[1]}"
        )
    if X.shape[2] != feature_count:
        raise ValueError(
            f"{split_name}: feature count mismatch: expected {feature_count}, got {X.shape[2]}"
        )
    if y.size and not set(np.unique(y)).issubset({0, 1}):
        raise ValueError(f"{split_name}: y contains values other than 0 and 1")
    if np.isnan(X).any():
        raise ValueError(f"{split_name}: X contains NaN values")
    if np.isinf(X).any():
        raise ValueError(f"{split_name}: X contains infinite values")


def verify_split_membership(
    split_name: str,
    manifest_patient_to_split: dict[str, str],
    seen_patient_splits: dict[str, str],
) -> set[str]:
    expected_patient_ids = {
        patient_id
        for patient_id, split in manifest_patient_to_split.items()
        if split == split_name
    }
    observed_patient_ids: set[str] = set()
    processed_path = PROCESSED_ROOT / f"{split_name}.csv"

    for chunk in pd.read_csv(processed_path, chunksize=100_000):
        patient_ids = chunk["patient_id"].astype(str)
        for patient_id in patient_ids:
            if patient_id not in manifest_patient_to_split:
                raise ValueError(
                    f"{split_name}: processed patient {patient_id} is not in the manifest."
                )
            if manifest_patient_to_split[patient_id] != split_name:
                raise ValueError(
                    f"{split_name}: patient {patient_id} belongs to a different manifest split."
                )

            if patient_id in seen_patient_splits:
                previous_split = seen_patient_splits[patient_id]
                if previous_split != split_name:
                    raise ValueError(
                        f"Patient {patient_id} appears in multiple processed splits: {previous_split} and {split_name}."
                    )
            else:
                seen_patient_splits[patient_id] = split_name

            observed_patient_ids.add(patient_id)

    if observed_patient_ids != expected_patient_ids:
        missing = sorted(expected_patient_ids - observed_patient_ids)
        extra = sorted(observed_patient_ids - expected_patient_ids)
        raise ValueError(
            f"{split_name}: processed patient IDs do not match manifest assignment. Missing={missing[:10]}, Extra={extra[:10]}"
        )

    return observed_patient_ids


def validate_global_coverage(
    manifest_patient_to_split: dict[str, str], observed_by_split: dict[str, set[str]]
) -> None:
    manifest_patient_ids = set(manifest_patient_to_split)
    all_observed = (
        set().union(*observed_by_split.values()) if observed_by_split else set()
    )

    if manifest_patient_ids != all_observed:
        missing = sorted(manifest_patient_ids - all_observed)
        extra = sorted(all_observed - manifest_patient_ids)
        raise ValueError(
            f"Global coverage mismatch. Missing={missing[:10]}, Extra={extra[:10]}"
        )

    seen: dict[str, str] = {}
    for split_name, patient_ids in observed_by_split.items():
        for patient_id in patient_ids:
            if patient_id in seen and seen[patient_id] != split_name:
                raise ValueError(
                    f"Patient {patient_id} appears in multiple processed splits: {seen[patient_id]} and {split_name}"
                )
            seen[patient_id] = split_name


def generate_sequence_metadata(
    split_summaries: dict[str, dict[str, int]],
    feature_names: list[str],
    source_files: dict[str, str],
) -> dict[str, object]:
    return {
        "sequence_length": SEQUENCE_LENGTH,
        "feature_names": feature_names,
        "number_of_features": len(feature_names),
        "num_train_sequences": int(split_summaries["train"]["sequences"]),
        "num_validation_sequences": int(split_summaries["validation"]["sequences"]),
        "num_test_sequences": int(split_summaries["test"]["sequences"]),
        "positive_sequence_count": int(
            split_summaries["train"]["positive"]
            + split_summaries["validation"]["positive"]
            + split_summaries["test"]["positive"]
        ),
        "negative_sequence_count": int(
            split_summaries["train"]["negative"]
            + split_summaries["validation"]["negative"]
            + split_summaries["test"]["negative"]
        ),
        "temporal_continuity_rule": "A valid sequence uses 12 consecutive ICU time steps with ICULOS differences of exactly 1. Any window with a gap is skipped.",
        "source_processed_files": source_files,
    }


def main() -> None:
    metadata_feature_names = load_feature_names()
    feature_names = filter_input_feature_names(metadata_feature_names)
    verify_feature_names(feature_names)
    SEQUENCE_ROOT.mkdir(parents=True, exist_ok=True)

    print(f"LSTM input features ({len(feature_names)}): {feature_names}")

    manifest_patient_to_split, _, _ = load_manifest_split_map()
    observed_by_split: dict[str, set[str]] = {}
    seen_patient_splits: dict[str, str] = {}

    for split_name in SPLIT_NAMES:
        observed_patient_ids = verify_split_membership(
            split_name, manifest_patient_to_split, seen_patient_splits
        )
        observed_by_split[split_name] = observed_patient_ids

    validate_global_coverage(manifest_patient_to_split, observed_by_split)

    split_summaries: dict[str, dict[str, int]] = {}
    for split_name in SPLIT_NAMES:
        summary = count_split_sequences(split_name, feature_names)
        split_summaries[split_name] = summary

        total_sequences = summary["sequences"]
        filled_summary = fill_split_sequences(
            split_name, feature_names, total_sequences
        )
        split_summaries[split_name] = filled_summary

    source_files = {
        split_name: str(PROCESSED_ROOT / f"{split_name}.csv")
        for split_name in SPLIT_NAMES
    }
    sequence_metadata = generate_sequence_metadata(
        split_summaries, feature_names, source_files
    )

    metadata_path = SEQUENCE_ROOT / "sequence_metadata.json"
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(sequence_metadata, handle, indent=2)

    print("\nTRAIN:")
    print(f"  sequences: {split_summaries['train']['sequences']}")
    print(f"  positive: {split_summaries['train']['positive']}")
    print(f"  negative: {split_summaries['train']['negative']}")
    print(f"  skipped windows: {split_summaries['train']['skipped_windows']}")

    print("\nVALIDATION:")
    print(f"  sequences: {split_summaries['validation']['sequences']}")
    print(f"  positive: {split_summaries['validation']['positive']}")
    print(f"  negative: {split_summaries['validation']['negative']}")
    print(f"  skipped windows: {split_summaries['validation']['skipped_windows']}")

    print("\nTEST:")
    print(f"  sequences: {split_summaries['test']['sequences']}")
    print(f"  positive: {split_summaries['test']['positive']}")
    print(f"  negative: {split_summaries['test']['negative']}")
    print(f"  skipped windows: {split_summaries['test']['skipped_windows']}")

    print("\nFINAL SUMMARY: PASS")


if __name__ == "__main__":
    main()
