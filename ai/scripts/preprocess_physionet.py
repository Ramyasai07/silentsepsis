#!/usr/bin/env python3
"""Leakage-safe preprocessing pipeline for the PhysioNet Challenge 2019 dataset.

This script reads the raw PSV patient files one at a time, preserves the existing
train/validation/test split, and writes processed CSV outputs under ai/data/processed/
without modifying the raw dataset files.

The preprocessing follows the official PhysioNet SepsisLabel semantics directly as the
prediction target. It uses patient-level forward fill followed by train-only medians,
creates missingness indicators before imputation, and learns categorical mappings from
TRAIN only.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = REPO_ROOT / "ai" / "data" / "raw"
SPLIT_MANIFEST = REPO_ROOT / "ai" / "data" / "splits" / "patient_split_manifest.csv"
PROCESSED_ROOT = REPO_ROOT / "ai" / "data" / "processed"
SPLIT_NAMES = ["train", "validation", "test"]
CATEGORICAL_COLUMNS = ["Gender", "Unit1", "Unit2"]

EXPECTED_SOURCE_ROW_COUNTS = {
    "train": 1_090_448,
    "validation": 232_030,
    "test": 229_732,
}
EXPECTED_TOTAL_SOURCE_ROWS = 1_552_210


def load_split_manifest() -> pd.DataFrame:
    if not SPLIT_MANIFEST.exists():
        raise FileNotFoundError(f"Split manifest not found: {SPLIT_MANIFEST}")

    manifest = pd.read_csv(SPLIT_MANIFEST)
    for split_name in SPLIT_NAMES:
        if split_name not in set(manifest["split"]):
            raise ValueError(f"Split '{split_name}' is missing from the manifest.")
    return manifest


def read_patient_file(file_path: Path) -> pd.DataFrame:
    return pd.read_csv(
        file_path,
        sep="|",
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )


def is_missing_value(value: object) -> bool:
    if value is None:
        return True

    text = str(value).strip()
    if text == "":
        return True

    if text.lower() in {"nan", "n/a", "na", "null", "none"}:
        return True

    return False


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.strip(), errors="coerce")


def build_patient_target(patient_df: pd.DataFrame) -> pd.Series:
    required_cols = {"ICULOS", "SepsisLabel"}
    missing_cols = required_cols - set(patient_df.columns)
    if missing_cols:
        raise ValueError(f"Patient file missing required columns: {sorted(missing_cols)}")

    patient_df = patient_df.copy()
    patient_df["ICULOS"] = pd.to_numeric(patient_df["ICULOS"], errors="coerce")
    patient_df["SepsisLabel"] = pd.to_numeric(patient_df["SepsisLabel"], errors="coerce")

    patient_df = patient_df[patient_df["ICULOS"].notna()].sort_values("ICULOS", kind="mergesort")
    patient_df = patient_df.reset_index(drop=True)

    first_positive_time = None
    for _, row in patient_df.iterrows():
        if pd.notna(row["SepsisLabel"]) and row["SepsisLabel"] == 1:
            first_positive_time = float(row["ICULOS"])
            break

    if first_positive_time is None:
        return pd.Series([0] * len(patient_df), index=patient_df.index, dtype=int)

    labels = []
    for _, row in patient_df.iterrows():
        current_time = float(row["ICULOS"])
        label = 1 if current_time >= first_positive_time else 0
        labels.append(int(label))

    return pd.Series(labels, index=patient_df.index, dtype=int)


def prepare_patient_frame(patient_df: pd.DataFrame, patient_id: str) -> pd.DataFrame:
    df = patient_df.copy()
    df["patient_id"] = patient_id

    if "ICULOS" not in df.columns:
        raise ValueError(f"Patient {patient_id} is missing ICULOS")

    df["ICULOS"] = pd.to_numeric(df["ICULOS"], errors="coerce")
    df = df.sort_values("ICULOS", kind="mergesort").reset_index(drop=True)
    df["target"] = build_patient_target(df)
    return df


def get_numeric_feature_names(patient_df: pd.DataFrame) -> list[str]:
    excluded = {"patient_id", "file_path", "training_set", "split", "SepsisLabel", "target"}
    names = []
    for col in patient_df.columns:
        if col in excluded:
            continue
        if col in CATEGORICAL_COLUMNS:
            continue
        names.append(col)
    return names


def count_raw_psv_files() -> dict[str, int]:
    counts = {}
    for dataset_name in ["training_setA", "training_setB"]:
        dataset_dir = RAW_ROOT / dataset_name
        counts[dataset_name] = len([path for path in dataset_dir.glob("*.psv") if path.is_file()])
    counts["total"] = counts["training_setA"] + counts["training_setB"]
    return counts


def compute_source_row_counts(manifest: pd.DataFrame) -> dict[str, int]:
    counts = {split_name: 0 for split_name in SPLIT_NAMES}
    for _, row in manifest.iterrows():
        file_path = REPO_ROOT / row["file_path"]
        if not file_path.exists():
            raise FileNotFoundError(f"Manifest references missing file: {file_path}")
        counts[str(row["split"])] += len(read_patient_file(file_path))
    return counts


def learn_train_statistics(manifest: pd.DataFrame) -> tuple[dict[str, float], dict[str, dict[str, int | float]], list[str]]:
    train_rows = manifest[manifest["split"] == "train"].reset_index(drop=True)
    if train_rows.empty:
        raise ValueError("Train split is empty. Cannot learn train-only statistics.")

    numeric_feature_names = None
    collected_numeric_values: dict[str, list[float]] = defaultdict(list)

    for _, record in train_rows.iterrows():
        patient_df = read_patient_file(REPO_ROOT / record["file_path"])
        patient_df = prepare_patient_frame(patient_df, str(record["patient_id"]))

        if numeric_feature_names is None:
            numeric_feature_names = get_numeric_feature_names(patient_df)

        for feature in numeric_feature_names:
            if feature not in patient_df.columns:
                continue
            series = safe_numeric(patient_df[feature]).ffill()
            collected_numeric_values[feature].extend(
                float(value) for value in series.dropna().tolist()
            )

    if numeric_feature_names is None:
        raise ValueError("No numeric feature names were discovered in the training split.")

    medians = {
        feature: float(pd.Series(collected_numeric_values.get(feature, [])).median()) if collected_numeric_values.get(feature) else 0.0
        for feature in numeric_feature_names
    }

    categorical_mappings: dict[str, dict[str, int | float]] = {}
    for col in CATEGORICAL_COLUMNS:
        seen_values = set()
        for _, record in train_rows.iterrows():
            patient_df = read_patient_file(REPO_ROOT / record["file_path"])
            if col in patient_df.columns:
                seen_values.update(
                    str(value).strip()
                    for value in patient_df[col].astype(str).fillna("missing").tolist()
                )

        if col == "Gender":
            mapping = {"F": 0, "M": 1, "missing": -1}
            for value in sorted(seen_values):
                normalized = value.strip()
                if normalized in {"", "nan", "NaN", "Na", "NA", "N/A", "none"}:
                    continue
                mapping.setdefault(normalized, -1)
        else:
            mapping = {"missing": -1}
            for value in sorted(seen_values):
                normalized = value.strip()
                if normalized in {"", "nan", "NaN", "Na", "NA", "N/A", "none"}:
                    continue
                if normalized not in mapping:
                    mapping[normalized] = len(mapping)

        categorical_mappings[col] = mapping

    return medians, categorical_mappings, numeric_feature_names


def encode_category(value: object, mapping: dict[str, int | float]) -> float:
    if value is None:
        return float(mapping.get("missing", -1))

    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "n/a", "na", "null", "none"}:
        return float(mapping.get("missing", -1))

    return float(mapping.get(text, mapping.get("missing", -1)))


def process_patient_file(
    patient_df: pd.DataFrame,
    patient_id: str,
    numerical_features: list[str],
    train_medians: dict[str, float],
    categorical_mappings: dict[str, dict[str, int | float]],
) -> pd.DataFrame:
    df = prepare_patient_frame(patient_df, patient_id)
    df = df.sort_values("ICULOS", kind="mergesort").reset_index(drop=True)

    numeric_columns = []
    missing_indicator_columns = []

    for feature in numerical_features:
        if feature not in df.columns:
            continue

        numeric_values = safe_numeric(df[feature])
        df[f"{feature}_missing"] = numeric_values.isna().astype(int)
        missing_indicator_columns.append(f"{feature}_missing")

        df[feature] = numeric_values.ffill()
        df[feature] = df[feature].fillna(train_medians.get(feature, 0.0))
        numeric_columns.append(feature)

    for col in CATEGORICAL_COLUMNS:
        if col in df.columns:
            df[col] = df[col].map(lambda value: encode_category(value, categorical_mappings.get(col, {"missing": -1})))

    model_columns = numeric_columns + CATEGORICAL_COLUMNS + missing_indicator_columns
    result = df[["patient_id", *model_columns, "target"]].copy()
    result = result.reset_index(drop=True)

    if result[model_columns].isna().any().any():
        raise ValueError(f"NaN values remain in processed patient rows for patient {patient_id}")

    return result


def write_processed_split(
    split_name: str,
    manifest: pd.DataFrame,
    numerical_features: list[str],
    train_medians: dict[str, float],
    categorical_mappings: dict[str, dict[str, int | float]],
) -> None:
    output_path = PROCESSED_ROOT / f"{split_name}.csv"
    if output_path.exists():
        output_path.unlink()

    subset = manifest[manifest["split"] == split_name].reset_index(drop=True)
    header_written = False

    for _, record in subset.iterrows():
        file_path = REPO_ROOT / record["file_path"]
        patient_id = str(record["patient_id"])

        if not file_path.exists():
            raise FileNotFoundError(f"Missing patient file for {patient_id}: {file_path}")

        patient_df = read_patient_file(file_path)
        processed = process_patient_file(
            patient_df,
            patient_id,
            numerical_features,
            train_medians,
            categorical_mappings,
        )

        processed.to_csv(output_path, mode="a", index=False, header=not header_written)
        header_written = True
        del processed


def verify_split_csv(split_name: str, manifest: pd.DataFrame, expected_source_rows: dict[str, int]) -> set[str]:
    expected_split_ids = set(manifest.loc[manifest["split"] == split_name, "patient_id"].astype(str))
    seen_split_patient_ids: set[str] = set()
    total_rows = 0
    output_path = PROCESSED_ROOT / f"{split_name}.csv"

    for chunk in pd.read_csv(output_path, chunksize=100_000):
        if "patient_id" not in chunk.columns or "target" not in chunk.columns:
            raise ValueError(f"{split_name}: processed file is missing required columns")

        total_rows += len(chunk)

        if not set(chunk["target"].dropna().unique()).issubset({0, 1}):
            raise ValueError(f"{split_name}: target contains values other than 0 and 1")

        for patient_id in chunk["patient_id"].astype(str):
            seen_split_patient_ids.add(patient_id)

        feature_columns = [col for col in chunk.columns if col not in {"patient_id", "ICULOS", "target"}]
        if "target" in feature_columns:
            raise ValueError(f"{split_name}: target appears among model features")
        if chunk[feature_columns].isna().any().any():
            raise ValueError(f"{split_name}: unexpected NaN values remain in model features")

    if total_rows != expected_source_rows[split_name]:
        raise ValueError(
            f"{split_name}: processed row count ({total_rows}) does not match source rows ({expected_source_rows[split_name]})"
        )

    if seen_split_patient_ids != expected_split_ids:
        missing = sorted(expected_split_ids - seen_split_patient_ids)
        raise ValueError(f"{split_name}: missing patient IDs from processed CSV: {missing[:10]}")

    extra = sorted(seen_split_patient_ids - expected_split_ids)
    if extra:
        raise ValueError(f"{split_name}: processed CSV contains patient IDs not expected for this split: {extra[:10]}")

    return seen_split_patient_ids


def verify_raw_dataset_count() -> None:
    raw_counts = count_raw_psv_files()
    if raw_counts["training_setA"] != 20_336:
        raise ValueError(f"training_setA raw PSV count mismatch: expected 20336, found {raw_counts['training_setA']}")
    if raw_counts["training_setB"] != 20_000:
        raise ValueError(f"training_setB raw PSV count mismatch: expected 20000, found {raw_counts['training_setB']}")
    if raw_counts["total"] != 40_336:
        raise ValueError(f"Total raw PSV count mismatch: expected 40336, found {raw_counts['total']}")


def verify_processed_outputs(manifest: pd.DataFrame) -> dict[str, int]:
    source_row_counts = compute_source_row_counts(manifest)
    if source_row_counts != EXPECTED_SOURCE_ROW_COUNTS:
        raise ValueError(f"Source row counts mismatch: expected {EXPECTED_SOURCE_ROW_COUNTS}, found {source_row_counts}")

    total_source_rows = sum(source_row_counts.values())
    if total_source_rows != EXPECTED_TOTAL_SOURCE_ROWS:
        raise ValueError(f"Total source row count mismatch: expected {EXPECTED_TOTAL_SOURCE_ROWS}, found {total_source_rows}")

    verify_raw_dataset_count()

    manifest_patient_to_split: dict[str, str] = {}
    for _, row in manifest.iterrows():
        patient_id = str(row["patient_id"])
        split_name = str(row["split"])
        if patient_id in manifest_patient_to_split and manifest_patient_to_split[patient_id] != split_name:
            raise ValueError(f"Patient {patient_id} appears in multiple splits in the manifest.")
        manifest_patient_to_split[patient_id] = split_name

    processed_patient_to_split: dict[str, str] = {}
    for split_name in SPLIT_NAMES:
        processed_patient_ids = verify_split_csv(split_name, manifest, source_row_counts)
        for patient_id in processed_patient_ids:
            if patient_id in processed_patient_to_split and processed_patient_to_split[patient_id] != split_name:
                raise ValueError(f"Patient {patient_id} appears in multiple processed splits.")
            processed_patient_to_split[patient_id] = split_name

    manifest_patient_ids = set(manifest_patient_to_split)
    processed_patient_ids = set(processed_patient_to_split)
    if manifest_patient_ids != processed_patient_ids:
        missing = sorted(manifest_patient_ids - processed_patient_ids)
        extra = sorted(processed_patient_ids - manifest_patient_ids)
        raise ValueError(
            f"Processed outputs do not match manifest coverage. Missing={missing[:10]}, Extra={extra[:10]}"
        )

    for patient_id, split_name in manifest_patient_to_split.items():
        if patient_id not in processed_patient_to_split:
            raise ValueError(f"Manifest patient {patient_id} is missing from the processed outputs.")
        if processed_patient_to_split[patient_id] != split_name:
            raise ValueError(f"Patient {patient_id} is assigned to {processed_patient_to_split[patient_id]} in processed outputs, but to {split_name} in the manifest.")

    return source_row_counts


def main() -> None:
    print("Leakage-safe preprocessing for PhysioNet Challenge 2019")
    print(f"Data root: {RAW_ROOT}")
    print(f"Split manifest: {SPLIT_MANIFEST}")
    print(f"Processed output root: {PROCESSED_ROOT}\n")

    manifest = load_split_manifest()
    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)

    train_medians, categorical_mappings, numerical_features = learn_train_statistics(manifest)
    feature_columns = numerical_features + CATEGORICAL_COLUMNS + [f"{feature}_missing" for feature in numerical_features]

    for split_name in SPLIT_NAMES:
        write_processed_split(
            split_name,
            manifest,
            numerical_features,
            train_medians,
            categorical_mappings,
        )
        print(f"{split_name}.csv written: {PROCESSED_ROOT / f'{split_name}.csv'}")

    source_row_counts = verify_processed_outputs(manifest)

    metadata = {
        "feature_columns": feature_columns,
        "missingness_indicator_columns": [f"{feature}_missing" for feature in numerical_features],
        "categorical_mappings": {
            key: {str(k): float(v) if isinstance(v, float) else int(v) for k, v in value.items()}
            for key, value in categorical_mappings.items()
        },
        "training_medians": {key: float(value) for key, value in train_medians.items()},
        "num_train_rows": int(source_row_counts["train"]),
        "num_validation_rows": int(source_row_counts["validation"]),
        "num_test_rows": int(source_row_counts["test"]),
        "num_features": int(len(feature_columns)),
        "preprocessing_steps": [
            "Read raw PSV patient files one at a time",
            "Keep the existing train/validation/test split unchanged",
            "Sort by ICULOS within each patient",
            "Use the official PhysioNet SepsisLabel semantics directly as the target",
            "Exclude patient_id, file path, training_set, split, and SepsisLabel from model inputs",
            "Treat NaN/empty values as missing while preserving valid zero values",
            "Create missingness indicator columns for original numeric features",
            "Forward-fill within each patient using only previous observations",
            "Fill remaining missing numeric values with train-only medians",
            "Learn categorical mappings on TRAIN and reuse them on validation and test",
            "No model training, no scaling, and no sequence generation",
        ],
    }

    metadata_path = PROCESSED_ROOT / "preprocessing_metadata.json"
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    print(f"Metadata written: {metadata_path}")

    print("\nProcessed row counts:")
    for split_name in SPLIT_NAMES:
        print(f"- {split_name}: {source_row_counts[split_name]} rows")

    print("\nVerification checks:")
    print(f"- source row counts match expected values: PASS")
    print(f"- processed row counts match source row counts: PASS")
    print(f"- no patient appears in multiple splits: PASS")
    print(f"- target contains only 0 and 1: PASS")
    print(f"- no NaN remains in model features: PASS")
    print(f"- raw PSV file count is exactly 40336: PASS")
    print("\nFINAL SUMMARY: PASS")


if __name__ == "__main__":
    main()
