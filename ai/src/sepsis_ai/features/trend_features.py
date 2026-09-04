from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

BASELINE_WINDOW_HOURS = 6
ROLLING_WINDOW_SIZE = 3

VITAL_COLUMN_MAP = {
    "heart_rate": "HR",
    "respiratory_rate": "Resp",
    "spo2": "O2Sat",
    "temperature": "Temp",
    "systolic_bp": "SBP",
    "diastolic_bp": "DBP",
}


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _safe_zero(value: float) -> float:
    if value is None or not np.isfinite(float(value)):
        return 0.0
    value = float(value)
    return 0.0 if abs(value) < 1e-12 else value


def load_split_manifest(manifest_path: Path | str) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_path)
    required = {"patient_id", "split"}
    missing = required.difference(manifest.columns)
    if missing:
        raise ValueError(f"Split manifest missing required columns: {sorted(missing)}")
    if manifest["patient_id"].duplicated().any():
        raise ValueError("Split manifest contains duplicate patient IDs across splits.")
    return manifest


def load_processed_split_data(processed_root: Path | str) -> pd.DataFrame:
    processed_root = Path(processed_root)
    split_names = ["train", "validation", "test"]
    chunks = []
    for split_name in split_names:
        csv_path = processed_root / f"{split_name}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing processed split file: {csv_path}")
        frame = pd.read_csv(csv_path)
        if "patient_id" not in frame.columns:
            raise ValueError(f"Processed split {split_name} is missing patient_id.")
        if "ICULOS" not in frame.columns:
            raise ValueError(f"Processed split {split_name} is missing ICULOS.")
        if "target" not in frame.columns:
            raise ValueError(f"Processed split {split_name} is missing target.")
        frame = frame.copy()
        frame["split"] = split_name
        chunks.append(frame)
    combined = pd.concat(chunks, ignore_index=True)
    combined["ICULOS"] = pd.to_numeric(combined["ICULOS"], errors="coerce")
    combined["patient_id"] = combined["patient_id"].astype(str)
    return combined.sort_values(
        ["split", "patient_id", "ICULOS"], kind="mergesort"
    ).reset_index(drop=True)


def validate_split_manifest(manifest: pd.DataFrame, patient_ids: Iterable[str]) -> None:
    manifest_ids = set(manifest["patient_id"].astype(str).tolist())
    observed_ids = set(str(pid) for pid in patient_ids)
    missing = sorted(observed_ids.difference(manifest_ids))
    extra = sorted(manifest_ids.difference(observed_ids))
    if missing:
        raise ValueError(
            f"Processed patient IDs missing from split manifest: {missing[:10]}"
        )
    if extra:
        raise ValueError(
            f"Split manifest includes IDs not present in processed data: {extra[:10]}"
        )
    if manifest["patient_id"].duplicated().any():
        raise ValueError("Split manifest contains duplicate patient IDs across splits.")


def _patient_baseline(
    series: pd.Series,
    iculos: pd.Series,
    baseline_window_hours: int = BASELINE_WINDOW_HOURS,
) -> float:
    values = pd.to_numeric(series, errors="coerce")
    iculos_values = pd.to_numeric(iculos, errors="coerce")
    if values.empty:
        return 0.0

    baseline_mask = iculos_values <= baseline_window_hours
    baseline_values = values[baseline_mask].dropna()
    if baseline_values.empty:
        baseline_values = values.dropna()
    if baseline_values.empty:
        return 0.0
    return float(baseline_values.mean())


def _pct_deviation(current_value: float, baseline_value: float) -> float:
    current_value = float(current_value)
    baseline_value = float(baseline_value)
    if not np.isfinite(current_value) or not np.isfinite(baseline_value):
        return 0.0
    if abs(baseline_value) < 1e-12:
        return 0.0
    return float(((current_value - baseline_value) / baseline_value) * 100.0)


def _rolling_aggregate(
    values: pd.Series, window_size: int = ROLLING_WINDOW_SIZE
) -> pd.Series:
    rolling = values.rolling(window=window_size, min_periods=1)
    return rolling.mean(), rolling.std(ddof=0)


def engineer_patient_features(patient_df: pd.DataFrame) -> pd.DataFrame:
    patient_df = patient_df.sort_values("ICULOS", kind="mergesort").copy()
    patient_df["ICULOS"] = pd.to_numeric(patient_df["ICULOS"], errors="coerce")
    result = patient_df.copy()

    for feature_name, source_name in VITAL_COLUMN_MAP.items():
        if source_name not in result.columns:
            continue

        values = _safe_numeric(result[source_name])
        baseline_value = _patient_baseline(values, result["ICULOS"])
        baseline_col = f"{feature_name}_baseline"
        result[baseline_col] = baseline_value

        deviation_col = f"{feature_name}_deviation"
        result[deviation_col] = values - baseline_value

        pct_col = f"{feature_name}_pct_deviation"
        result[pct_col] = values.apply(
            lambda value: _pct_deviation(float(value), baseline_value)
        )

        delta_values = values.diff().fillna(0.0)
        delta_col = f"{feature_name}_delta"
        result[delta_col] = delta_values

        rolling_mean, rolling_std = _rolling_aggregate(values)
        result[f"{feature_name}_rolling_mean"] = rolling_mean.fillna(0.0)
        result[f"{feature_name}_rolling_std"] = rolling_std.fillna(0.0)

    if "HR" in result.columns and "SBP" in result.columns:
        hr_values = _safe_numeric(result["HR"])
        sbp_values = _safe_numeric(result["SBP"])
        shock_index = pd.Series(0.0, index=result.index, dtype=float)
        valid_mask = sbp_values.notna() & (sbp_values > 0)
        shock_index.loc[valid_mask] = (
            hr_values.loc[valid_mask] / sbp_values.loc[valid_mask]
        )
        result["shock_index"] = shock_index

    return result


def build_feature_table(processed_df: pd.DataFrame) -> pd.DataFrame:
    required = {"patient_id", "ICULOS", "target"}
    missing = required.difference(processed_df.columns)
    if missing:
        raise ValueError(f"Processed data missing required columns: {sorted(missing)}")

    rows = []
    for patient_id, group in processed_df.groupby("patient_id", sort=False):
        patient_features = engineer_patient_features(group)
        rows.append(patient_features)

    feature_table = pd.concat(rows, ignore_index=True)
    feature_table = feature_table.sort_values(
        ["split", "patient_id", "ICULOS"], kind="mergesort"
    ).reset_index(drop=True)
    return feature_table


def main() -> pd.DataFrame:
    processed_root = Path(__file__).resolve().parents[3] / "ai" / "data" / "processed"
    manifest_path = (
        Path(__file__).resolve().parents[3]
        / "ai"
        / "data"
        / "splits"
        / "patient_split_manifest.csv"
    )
    frame = load_processed_split_data(processed_root)
    manifest = load_split_manifest(manifest_path)
    validate_split_manifest(manifest, frame["patient_id"].dropna().unique())
    feature_table = build_feature_table(frame)
    return feature_table
