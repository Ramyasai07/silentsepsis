"""Stateless feature construction shared by offline training and runtime inference."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pandas as pd

ONLINE_FEATURE_COLUMNS = (
    "HR",
    "O2Sat",
    "Temp",
    "SBP",
    "DBP",
    "Resp",
    "MAP",
    "Age",
    "Gender",
    "HR_missing",
    "O2Sat_missing",
    "Temp_missing",
    "SBP_missing",
    "DBP_missing",
    "Resp_missing",
)
VITAL_SOURCE_COLUMNS = ("HR", "O2Sat", "Temp", "SBP", "DBP", "Resp")
GENDER_MAPPING = {"FEMALE": 0, "MALE": 1, "OTHER": -1, "UNKNOWN": -1}
MISSING_TOKENS = {"", "nan", "na", "n/a", "null", "none"}


def online_metadata() -> dict[str, object]:
    return {
        "preprocessing_version": "online-stateless-v1",
        "feature_columns": list(ONLINE_FEATURE_COLUMNS),
        "num_features": len(ONLINE_FEATURE_COLUMNS),
        "source_columns": {
            "HR": "HR",
            "O2Sat": "O2Sat",
            "Temp": "Temp",
            "SBP": "SBP",
            "DBP": "DBP",
            "Resp": "Resp",
            "MAP": ["SBP", "DBP"],
            "Age": "Age",
            "Gender": "Gender",
        },
        "transformations": {
            "MAP": "(SBP + 2 * DBP) / 3 when both source values are present",
            "numeric_features": (
                (
                    "Parse current-row values as numeric; invalid or missing "
                    "values remain null"
                )
            ),
            "Gender": (
                "FEMALE=0, MALE=1, OTHER=1, UNKNOWN=-1; " "PhysioNet 0=0 and 1=1"
            ),
            "missingness": (
                "Indicators are computed from original current-row values "
                "before transformation"
            ),
        },
        "gender_mapping": GENDER_MAPPING,
        "missingness_definitions": {
            f"{column}_missing": (
                f"1 when original {column} is missing or invalid, otherwise 0"
            )
            for column in VITAL_SOURCE_COLUMNS
        },
        "imputation_policy": "none; missing values remain null",
        "forward_fill": False,
        "history_required": False,
        "split_provenance": "patient_split_manifest.csv",
    }


def is_missing_value(value: object) -> bool:
    return value is None or str(value).strip().lower() in MISSING_TOKENS


def numeric_value(value: object) -> float | None:
    if is_missing_value(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def gender_value(value: object) -> int:
    if is_missing_value(value):
        return -1
    normalized = str(value).strip().upper()
    if normalized in GENDER_MAPPING:
        return GENDER_MAPPING[normalized]
    if normalized == "0":
        return 0
    if normalized == "1":
        return 1
    raise ValueError(f"Unsupported Gender value: {value}")


def transform_online_row(
    row: dict[str, object] | pd.Series
) -> dict[str, float | int | None]:
    values = {column: numeric_value(row.get(column)) for column in VITAL_SOURCE_COLUMNS}
    values["MAP"] = (
        (values["SBP"] + 2 * values["DBP"]) / 3
        if values["SBP"] is not None and values["DBP"] is not None
        else None
    )
    values["Age"] = numeric_value(row.get("Age"))
    values["Gender"] = gender_value(row.get("Gender"))
    for source_column in VITAL_SOURCE_COLUMNS:
        values[f"{source_column}_missing"] = int(
            is_missing_value(row.get(source_column))
        )
    return {column: values[column] for column in ONLINE_FEATURE_COLUMNS}


def transform_online_frame(frame: pd.DataFrame) -> pd.DataFrame:
    transformed = pd.DataFrame(
        [transform_online_row(row) for row in frame.to_dict(orient="records")],
        columns=ONLINE_FEATURE_COLUMNS,
    )
    return transformed


def load_split_manifest(path: Path) -> pd.DataFrame:
    manifest = pd.read_csv(path, dtype={"patient_id": str})
    required_columns = {"patient_id", "split", "training_set", "file_path"}
    missing_columns = required_columns - set(manifest.columns)
    if missing_columns:
        raise ValueError(f"Manifest missing columns: {sorted(missing_columns)}")
    if manifest["patient_id"].duplicated().any():
        raise ValueError("Manifest contains duplicate patient IDs")
    split_sets = {
        split: set(manifest.loc[manifest["split"] == split, "patient_id"])
        for split in ("train", "validation", "test")
    }
    for first, second in combinations(split_sets, 2):
        if split_sets[first] & split_sets[second]:
            raise ValueError(f"Patient leakage detected between {first} and {second}")
    if len(set().union(*split_sets.values())) != len(manifest):
        raise ValueError("Manifest contains an unknown split")
    return manifest
