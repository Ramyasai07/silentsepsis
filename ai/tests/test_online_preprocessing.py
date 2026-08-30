from pathlib import Path

import pandas as pd
import pytest

from ai.ml.online_preprocessing import (
    ONLINE_FEATURE_COLUMNS,
    load_split_manifest,
    online_metadata,
    transform_online_frame,
    transform_online_row,
)


def complete_row(**overrides: object) -> dict[str, object]:
    row = {
        "HR": "80",
        "O2Sat": "98",
        "Temp": "37.0",
        "SBP": "120",
        "DBP": "60",
        "Resp": "18",
        "Age": "64",
        "Gender": "MALE",
        "EtCO2": "unavailable",
        "Lactate": "unavailable",
    }
    row.update(overrides)
    return row


def test_physionet_row_produces_exactly_fifteen_ordered_features() -> None:
    transformed = transform_online_row(complete_row())

    assert list(transformed) == list(ONLINE_FEATURE_COLUMNS)
    assert len(transformed) == 15


def test_map_is_derived_correctly() -> None:
    assert transform_online_row(complete_row())["MAP"] == 80.0


def test_missingness_uses_original_values_before_transformation() -> None:
    transformed = transform_online_row(complete_row(SBP="", DBP="60"))

    assert transformed["SBP"] is None
    assert transformed["SBP_missing"] == 1
    assert transformed["DBP_missing"] == 0
    assert transformed["MAP"] is None


@pytest.mark.parametrize(
    ("gender", "expected"),
    [("FEMALE", 0), ("MALE", 1), ("OTHER", -1), ("UNKNOWN", -1), ("0", 0), ("1", 1)],
)
def test_gender_mapping_is_deterministic(gender: str, expected: int) -> None:
    assert transform_online_row(complete_row(Gender=gender))["Gender"] == expected


def test_no_forward_fill_occurs() -> None:
    frame = pd.DataFrame([complete_row(HR=""), complete_row(HR="90")])

    transformed = transform_online_frame(frame)

    assert transformed.loc[0, "HR"] != transformed.loc[1, "HR"]
    assert pd.isna(transformed.loc[0, "HR"])
    assert transformed.loc[0, "HR_missing"] == 1


def test_unavailable_features_are_not_introduced() -> None:
    transformed = transform_online_row(complete_row())

    assert set(transformed) == set(ONLINE_FEATURE_COLUMNS)
    assert "EtCO2" not in transformed
    assert "Lactate" not in transformed
    assert "HospAdmTime" not in transformed


def test_same_logical_input_is_deterministic() -> None:
    first = transform_online_row(complete_row())
    second = transform_online_row(complete_row())

    assert first == second


def test_manifest_assignments_are_disjoint_and_match_existing_manifest() -> None:
    manifest_path = Path("ai/data/splits/patient_split_manifest.csv")
    manifest = load_split_manifest(manifest_path)

    assert manifest.groupby("split")["patient_id"].nunique().to_dict() == {
        "train": 28233,
        "validation": 6049,
        "test": 6054,
    }
    assert len(manifest) == 40336
    assert not manifest["patient_id"].duplicated().any()
    assert set(manifest.loc[manifest.split == "train", "patient_id"]).isdisjoint(
        set(manifest.loc[manifest.split == "validation", "patient_id"])
    )
    assert set(manifest.loc[manifest.split == "train", "patient_id"]).isdisjoint(
        set(manifest.loc[manifest.split == "test", "patient_id"])
    )
    assert set(manifest.loc[manifest.split == "validation", "patient_id"]).isdisjoint(
        set(manifest.loc[manifest.split == "test", "patient_id"])
    )


def test_metadata_feature_order_matches_transformer() -> None:
    metadata = online_metadata()
    assert len(ONLINE_FEATURE_COLUMNS) == 15
    assert metadata["feature_columns"] == list(ONLINE_FEATURE_COLUMNS)
    assert metadata["num_features"] == 15
    assert "HospAdmTime" not in ONLINE_FEATURE_COLUMNS
    assert "ICULOS" not in ONLINE_FEATURE_COLUMNS
    assert "target" not in ONLINE_FEATURE_COLUMNS
    assert "patient_id" not in ONLINE_FEATURE_COLUMNS