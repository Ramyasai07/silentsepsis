#!/usr/bin/env python3
"""Read-only directional SHAP analysis for the final Experiment 2 LSTM model."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

try:
    import shap
except Exception as exc:  # pragma: no cover - SHAP is required for this script
    raise RuntimeError(
        "SHAP is required for this analysis but is not installed."
    ) from exc

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - optional plotting dependency
    plt = None

REPO_ROOT = Path(__file__).resolve().parents[2]
SEQUENCE_ROOT = REPO_ROOT / "ai" / "data" / "sequences"
MODEL_ROOT = REPO_ROOT / "ai" / "models"
SEQUENCE_METADATA_PATH = SEQUENCE_ROOT / "sequence_metadata.json"
NORMALIZATION_STATS_PATH = MODEL_ROOT / "lstm_normalization_stats.json"
MODEL_PATH = MODEL_ROOT / "lstm_best.keras"

BACKGROUND_SAMPLES = 50
EXPLANATION_SAMPLES = 100
RANDOM_SEED = 42
THRESHOLD = 0.85


def load_metadata() -> dict:
    if not SEQUENCE_METADATA_PATH.exists():
        raise FileNotFoundError(f"Missing sequence metadata: {SEQUENCE_METADATA_PATH}")

    with SEQUENCE_METADATA_PATH.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)

    required = {"sequence_length", "feature_names", "number_of_features"}
    missing = sorted(required - metadata.keys())
    if missing:
        raise ValueError(f"sequence_metadata.json is missing required keys: {missing}")

    return metadata


def load_normalization_stats() -> tuple[np.ndarray, np.ndarray]:
    if not NORMALIZATION_STATS_PATH.exists():
        raise FileNotFoundError(
            f"Missing normalization stats: {NORMALIZATION_STATS_PATH}"
        )

    with NORMALIZATION_STATS_PATH.open("r", encoding="utf-8") as handle:
        stats = json.load(handle)

    train_mean = np.asarray(stats["means"], dtype=np.float64)
    train_std = np.asarray(stats["standard_deviations"], dtype=np.float64)
    return train_mean, train_std


def load_memmap_split(split_name: str) -> tuple[np.ndarray, np.ndarray]:
    x_path = SEQUENCE_ROOT / f"{split_name}_X.npy"
    y_path = SEQUENCE_ROOT / f"{split_name}_y.npy"

    if not x_path.exists():
        raise FileNotFoundError(f"Missing X array: {x_path}")
    if not y_path.exists():
        raise FileNotFoundError(f"Missing y array: {y_path}")

    X = np.load(x_path, mmap_mode="r", allow_pickle=False)
    y = np.load(y_path, mmap_mode="r", allow_pickle=False)

    if not isinstance(X, np.memmap):
        raise ValueError(f"{split_name}: X is not memory-mappable: {type(X)}")
    if not isinstance(y, np.memmap):
        raise ValueError(f"{split_name}: y is not memory-mappable: {type(y)}")

    return X, y


def verify_split(
    X: np.ndarray,
    y: np.ndarray,
    split_name: str,
    sequence_length: int,
    feature_count: int,
) -> None:
    if X.shape[0] != y.shape[0]:
        raise ValueError(
            f"{split_name}: X and y sample counts do not match ({X.shape[0]} vs {y.shape[0]})"
        )
    if X.ndim != 3:
        raise ValueError(f"{split_name}: X is not 3-dimensional; shape={X.shape}")
    if X.shape[1] != sequence_length:
        raise ValueError(
            f"{split_name}: sequence length mismatch; expected {sequence_length}, found {X.shape[1]}"
        )
    if X.shape[2] != feature_count:
        raise ValueError(
            f"{split_name}: feature count mismatch; expected {feature_count}, found {X.shape[2]}"
        )
    if y.size == 0:
        raise ValueError(f"{split_name}: y is empty.")
    if not set(np.unique(y)).issubset({0, 1}):
        raise ValueError(f"{split_name}: y contains values other than 0 and 1")

    chunk_size = 8192
    for start in range(0, X.shape[0], chunk_size):
        stop = min(start + chunk_size, X.shape[0])
        chunk = X[start:stop]

        if np.isnan(chunk).any():
            raise ValueError(f"{split_name}: X contains NaN values")
        if np.isinf(chunk).any():
            raise ValueError(f"{split_name}: X contains infinite values")


def select_explanation_subset(
    X_test: np.ndarray, y_test: np.ndarray
) -> tuple[np.ndarray, np.ndarray, int, int, int]:
    positive_idx = np.where(y_test == 1)[0]
    negative_idx = np.where(y_test == 0)[0]

    rng = np.random.default_rng(RANDOM_SEED)
    positive_choice = (
        positive_idx
        if len(positive_idx) <= 50
        else rng.choice(positive_idx, size=50, replace=False)
    )
    negative_choice = (
        negative_idx
        if len(negative_idx) <= 50
        else rng.choice(negative_idx, size=50, replace=False)
    )

    selected = np.concatenate([positive_choice, negative_choice])
    selected = selected[:EXPLANATION_SAMPLES]

    if len(selected) == 0:
        raise ValueError("No explanation samples were selected from the test split.")

    return (
        X_test[selected],
        y_test[selected],
        int(np.sum(y_test[selected] == 1)),
        int(np.sum(y_test[selected] == 0)),
        int(len(selected)),
    )


def get_background_data(
    train_X: np.ndarray, train_mean: np.ndarray, train_std: np.ndarray
) -> np.ndarray:
    total_samples = min(train_X.shape[0], BACKGROUND_SAMPLES)
    idx = np.random.default_rng(RANDOM_SEED).choice(
        train_X.shape[0], size=total_samples, replace=False
    )
    background = train_X[idx]
    return (background - train_mean) / train_std


def normalize_batch(batch: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return (batch - mean) / std


def validate_shap_shape(
    shap_array: np.ndarray,
    expected_shape: tuple[int, int, int],
    feature_names: list[str],
) -> None:
    if shap_array is None:
        raise ValueError("SHAP values are None.")
    if shap_array.shape != expected_shape:
        raise ValueError(
            f"SHAP values do not match expected dimensions: expected {expected_shape}, got {shap_array.shape}"
        )
    if len(feature_names) != expected_shape[2]:
        raise ValueError(
            f"Feature count mismatch: expected {expected_shape[2]}, got {len(feature_names)}"
        )
    if np.isnan(shap_array).any():
        raise ValueError("SHAP values contain NaN values.")
    if np.isinf(shap_array).any():
        raise ValueError("SHAP values contain infinite values.")


def prepare_shap_array(
    shap_values: object, expected_samples: int, sequence_length: int, feature_count: int
) -> np.ndarray:
    if isinstance(shap_values, list):
        if len(shap_values) != 1:
            raise ValueError(
                f"Unsupported SHAP output structure: list of length {len(shap_values)}"
            )
        shap_array = np.asarray(shap_values[0])
    else:
        shap_array = np.asarray(shap_values)

    if shap_array.ndim == 4:
        if shap_array.shape[-1] != 1:
            raise ValueError(f"Unsupported SHAP output shape: {shap_array.shape}")
        shap_array = shap_array[..., 0]

    if shap_array.ndim == 2:
        if shap_array.shape != (expected_samples * sequence_length, feature_count):
            raise ValueError(f"Unsupported SHAP output shape: {shap_array.shape}")
        shap_array = shap_array.reshape(
            expected_samples, sequence_length, feature_count
        )

    if shap_array.shape != (expected_samples, sequence_length, feature_count):
        raise ValueError(
            f"SHAP values do not match model input dimensions: expected {(expected_samples, sequence_length, feature_count)}, got {shap_array.shape}"
        )

    return shap_array


def compute_feature_direction(
    shap_values: np.ndarray, feature_names: list[str]
) -> pd.DataFrame:
    mean_signed = np.mean(shap_values, axis=(0, 1))
    mean_abs = np.mean(np.abs(shap_values), axis=(0, 1))
    positive_fraction = np.mean(shap_values > 0, axis=(0, 1))
    negative_fraction = np.mean(shap_values < 0, axis=(0, 1))

    df = pd.DataFrame(
        {
            "feature": feature_names,
            "mean_signed_shap": mean_signed.astype(float),
            "mean_absolute_shap": mean_abs.astype(float),
            "positive_shap_fraction": positive_fraction.astype(float),
            "negative_shap_fraction": negative_fraction.astype(float),
        }
    )
    return df


def compute_timestep_direction(shap_values: np.ndarray) -> pd.DataFrame:
    mean_signed = np.mean(shap_values, axis=(0, 2))
    mean_abs = np.mean(np.abs(shap_values), axis=(0, 2))
    positive_fraction = np.mean(shap_values > 0, axis=(0, 2))
    negative_fraction = np.mean(shap_values < 0, axis=(0, 2))

    rows = []
    for timestep_idx in range(12):
        rows.append(
            {
                "timestep": timestep_idx + 1,
                "mean_signed_shap": float(mean_signed[timestep_idx]),
                "mean_absolute_shap": float(mean_abs[timestep_idx]),
                "positive_shap_fraction": float(positive_fraction[timestep_idx]),
                "negative_shap_fraction": float(negative_fraction[timestep_idx]),
            }
        )
    return pd.DataFrame(rows)


def create_positive_contributor_plot(
    feature_df: pd.DataFrame, output_path: Path
) -> None:
    if plt is None:
        return

    top = (
        feature_df.sort_values("mean_signed_shap", ascending=False).head(20).iloc[::-1]
    )
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.barh(top["feature"], top["mean_signed_shap"])
    ax.invert_yaxis()
    ax.set_title("Experiment 2 LSTM — Positive Contributors")
    ax.set_xlabel("Mean signed SHAP")
    ax.set_ylabel("Feature")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def create_negative_contributor_plot(
    feature_df: pd.DataFrame, output_path: Path
) -> None:
    if plt is None:
        return

    top = feature_df.sort_values("mean_signed_shap", ascending=True).head(20).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.barh(top["feature"], top["mean_signed_shap"])
    ax.invert_yaxis()
    ax.set_title("Experiment 2 LSTM — Negative Contributors")
    ax.set_xlabel("Mean signed SHAP")
    ax.set_ylabel("Feature")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing trained model: {MODEL_PATH}")

    metadata = load_metadata()
    sequence_length = int(metadata["sequence_length"])
    feature_names = list(metadata["feature_names"])
    feature_count = int(metadata["number_of_features"])

    if feature_count != 76:
        raise ValueError(f"Expected 76 features, found {feature_count}")
    if len(feature_names) != 76:
        raise ValueError(f"Expected 76 feature names, found {len(feature_names)}")

    train_mean, train_std = load_normalization_stats()
    if train_mean.shape[0] != feature_count or train_std.shape[0] != feature_count:
        raise ValueError(
            "Normalization statistics do not match the expected feature count."
        )

    X_train, y_train = load_memmap_split("train")
    verify_split(X_train, y_train, "train", sequence_length, feature_count)

    X_test, y_test = load_memmap_split("test")
    verify_split(X_test, y_test, "test", sequence_length, feature_count)

    background = get_background_data(X_train, train_mean, train_std)
    (
        explanation_X,
        explanation_y,
        positive_explanation,
        negative_explanation,
        explanation_count,
    ) = select_explanation_subset(X_test, y_test)
    explanation_X_norm = normalize_batch(explanation_X, train_mean, train_std)

    if background.shape[0] > BACKGROUND_SAMPLES:
        raise ValueError(
            f"Background sample count exceeds limit: {background.shape[0]} > {BACKGROUND_SAMPLES}"
        )
    if explanation_count > EXPLANATION_SAMPLES:
        raise ValueError(
            f"Explanation sample count exceeds limit: {explanation_count} > {EXPLANATION_SAMPLES}"
        )

    model = tf.keras.models.load_model(MODEL_PATH)
    input_shape = model.input_shape
    flatten_input_shape = (
        tuple(int(value) for value in input_shape[1:])
        if isinstance(input_shape, (list, tuple)) and len(input_shape) > 1
        else None
    )
    if flatten_input_shape is None:
        raise ValueError("Could not determine the model input shape.")
    if flatten_input_shape != (12, 76):
        raise ValueError(
            f"Unexpected model input shape: {flatten_input_shape}; expected (12, 76)"
        )

    model_prob = model.predict(explanation_X_norm, batch_size=256, verbose=0).reshape(
        -1
    )
    pred_positive = int(np.sum(model_prob >= THRESHOLD))
    pred_negative = int(np.sum(model_prob < THRESHOLD))

    explainer = shap.GradientExplainer(model, background)
    shap_values = explainer.shap_values(explanation_X_norm, nsamples=50)
    shap_array = prepare_shap_array(
        shap_values, explanation_count, sequence_length, feature_count
    )
    validate_shap_shape(
        shap_array, (explanation_count, sequence_length, feature_count), feature_names
    )

    overall_feature_df = compute_feature_direction(shap_array, feature_names)
    overall_feature_df = overall_feature_df.sort_values(
        "mean_absolute_shap", ascending=False
    ).reset_index(drop=True)
    overall_feature_df.insert(
        0, "rank_overall", np.arange(1, len(overall_feature_df) + 1)
    )

    positive_rank_df = overall_feature_df.sort_values(
        "mean_signed_shap", ascending=False
    ).reset_index(drop=True)
    positive_rank_df.insert(0, "rank_positive", np.arange(1, len(positive_rank_df) + 1))

    negative_rank_df = overall_feature_df.sort_values(
        "mean_signed_shap", ascending=True
    ).reset_index(drop=True)
    negative_rank_df.insert(0, "rank_negative", np.arange(1, len(negative_rank_df) + 1))

    feature_combined = overall_feature_df.merge(
        positive_rank_df[["feature", "rank_positive"]], on="feature", how="left"
    )
    feature_combined = feature_combined.merge(
        negative_rank_df[["feature", "rank_negative"]], on="feature", how="left"
    )
    feature_combined = feature_combined[
        [
            "rank_overall",
            "rank_positive",
            "rank_negative",
            "feature",
            "mean_signed_shap",
            "mean_absolute_shap",
            "positive_shap_fraction",
            "negative_shap_fraction",
        ]
    ]

    timestep_direction = compute_timestep_direction(shap_array)

    subgroup_analysis = {
        "positive": None,
        "negative": None,
    }
    if positive_explanation > 0 and negative_explanation > 0:
        pos_mask = explanation_y == 1
        neg_mask = explanation_y == 0
        subgroup_analysis["positive"] = compute_feature_direction(
            shap_array[pos_mask], feature_names
        ).to_dict(orient="records")
        subgroup_analysis["negative"] = compute_feature_direction(
            shap_array[neg_mask], feature_names
        ).to_dict(orient="records")
    else:
        subgroup_analysis["positive"] = (
            "SKIPPED: insufficient positive or negative explanation samples"
        )
        subgroup_analysis["negative"] = (
            "SKIPPED: insufficient positive or negative explanation samples"
        )

    feature_combined.to_csv(
        MODEL_ROOT / "lstm_shap_directional_features.csv", index=False
    )
    timestep_direction.to_csv(
        MODEL_ROOT / "lstm_shap_directional_timesteps.csv", index=False
    )

    analysis_payload = {
        "model_path": str(MODEL_PATH.relative_to(REPO_ROOT)),
        "normalization_stats_path": str(
            NORMALIZATION_STATS_PATH.relative_to(REPO_ROOT)
        ),
        "background_sample_count": int(background.shape[0]),
        "explanation_sample_count": int(explanation_count),
        "positive_explanation_sample_count": int(positive_explanation),
        "negative_explanation_sample_count": int(negative_explanation),
        "model_input_shape": [sequence_length, feature_count],
        "shap_value_shape": list(shap_array.shape),
        "threshold": float(THRESHOLD),
        "prediction_summary": {
            "predicted_positive": int(pred_positive),
            "predicted_negative": int(pred_negative),
        },
        "overall_top_20": feature_combined.head(20).to_dict(orient="records"),
        "positive_contributors": positive_rank_df.head(20).to_dict(orient="records"),
        "negative_contributors": negative_rank_df.head(20).to_dict(orient="records"),
        "timestep_direction": timestep_direction.to_dict(orient="records"),
        "positive_subgroup_analysis": subgroup_analysis["positive"],
        "negative_subgroup_analysis": subgroup_analysis["negative"],
    }
    with (MODEL_ROOT / "lstm_shap_direction_analysis.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(analysis_payload, handle, indent=2)

    if plt is not None:
        create_positive_contributor_plot(
            feature_combined, MODEL_ROOT / "lstm_shap_positive_contributors.png"
        )
        create_negative_contributor_plot(
            feature_combined, MODEL_ROOT / "lstm_shap_negative_contributors.png"
        )

    print("DIRECTIONAL SHAP ANALYSIS — EXPERIMENT 2")
    print("SAMPLES:")
    print(f"  background: {background.shape[0]}")
    print(f"  explanation: {explanation_count}")
    print(f"  positive: {positive_explanation}")
    print(f"  negative: {negative_explanation}")

    print("\nSHAP:")
    print(f"  shape: {shap_array.shape}")
    print(f"  NaN count: {int(np.isnan(shap_array).sum())}")
    print(f"  Inf count: {int(np.isinf(shap_array).sum())}")

    print("\nTOP POSITIVE CONTRIBUTORS:")
    for idx, row in positive_rank_df.head(20).iterrows():
        print(f"  {idx + 1}. {row['feature']} = {row['mean_signed_shap']:.6f}")
        print(f"     mean_signed_shap = {row['mean_signed_shap']:.6f}")
        print(f"     mean_absolute_shap = {row['mean_absolute_shap']:.6f}")
        print(f"     positive_fraction = {row['positive_shap_fraction']:.6f}")
        print(f"     negative_fraction = {row['negative_shap_fraction']:.6f}")

    print("\nTOP NEGATIVE CONTRIBUTORS:")
    for idx, row in negative_rank_df.head(20).iterrows():
        print(f"  {idx + 1}. {row['feature']} = {row['mean_signed_shap']:.6f}")
        print(f"     mean_signed_shap = {row['mean_signed_shap']:.6f}")
        print(f"     mean_absolute_shap = {row['mean_absolute_shap']:.6f}")
        print(f"     positive_fraction = {row['positive_shap_fraction']:.6f}")
        print(f"     negative_fraction = {row['negative_shap_fraction']:.6f}")

    print("\nTIMESTEP DIRECTION:")
    for _, row in timestep_direction.iterrows():
        print(f"  {int(row['timestep'])}: {float(row['mean_signed_shap']):.6f}")

    print("\nFINAL SUMMARY: PASS")


if __name__ == "__main__":
    main()
