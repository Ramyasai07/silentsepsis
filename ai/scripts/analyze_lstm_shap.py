#!/usr/bin/env python3
"""Read-only SHAP explainability analysis for the final Experiment 2 LSTM model."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

try:
    import shap
except Exception as exc:  # pragma: no cover - SHAP is required for this script
    raise RuntimeError("SHAP is required for this analysis but is not installed.") from exc

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
        raise FileNotFoundError(f"Missing normalization stats: {NORMALIZATION_STATS_PATH}")

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


def verify_split(X: np.ndarray, y: np.ndarray, split_name: str, sequence_length: int, feature_count: int) -> None:
    if X.shape[0] != y.shape[0]:
        raise ValueError(f"{split_name}: X and y sample counts do not match ({X.shape[0]} vs {y.shape[0]})")
    if X.ndim != 3:
        raise ValueError(f"{split_name}: X is not 3-dimensional; shape={X.shape}")
    if X.shape[1] != sequence_length:
        raise ValueError(f"{split_name}: sequence length mismatch; expected {sequence_length}, found {X.shape[1]}")
    if X.shape[2] != feature_count:
        raise ValueError(f"{split_name}: feature count mismatch; expected {feature_count}, found {X.shape[2]}")
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


def select_explanation_subset(X_test: np.ndarray, y_test: np.ndarray) -> tuple[np.ndarray, np.ndarray, int, int, int]:
    positive_idx = np.where(y_test == 1)[0]
    negative_idx = np.where(y_test == 0)[0]

    np.random.seed(42)
    positive_choice = positive_idx if len(positive_idx) <= 50 else np.random.choice(positive_idx, size=50, replace=False)
    negative_choice = negative_idx if len(negative_idx) <= 50 else np.random.choice(negative_idx, size=50, replace=False)

    positive_count = min(len(positive_choice), 50)
    negative_count = min(len(negative_choice), 50)
    total_samples = min(len(positive_choice) + len(negative_choice), EXPLANATION_SAMPLES)

    selected_positive = positive_choice[:positive_count]
    selected_negative = negative_choice[:negative_count]
    selected = np.concatenate([selected_positive, selected_negative])
    selected = selected[:total_samples]

    if len(selected) == 0:
        raise ValueError("No explanation samples were selected from the test split.")

    return X_test[selected], y_test[selected], int(np.sum(y_test[selected] == 1)), int(np.sum(y_test[selected] == 0)), int(len(selected))


def get_background_data(train_X: np.ndarray, train_mean: np.ndarray, train_std: np.ndarray) -> np.ndarray:
    total_samples = min(train_X.shape[0], BACKGROUND_SAMPLES)
    idx = np.random.default_rng(42).choice(train_X.shape[0], size=total_samples, replace=False)
    background = train_X[idx]
    return (background - train_mean) / train_std


def validate_shap_values(shap_values: np.ndarray, input_shape: tuple[int, int, int], feature_names: list[str]) -> None:
    if shap_values is None:
        raise ValueError("SHAP values are None.")

    if isinstance(shap_values, list):
        if len(shap_values) != 1:
            raise ValueError(f"Unsupported SHAP output structure: list of length {len(shap_values)}")
        shap_values = shap_values[0]

    shap_array = np.asarray(shap_values)
    if shap_array.ndim != 3:
        raise ValueError(f"SHAP values do not match model input dimensions: expected 3D shape, got {shap_array.shape}")
    if shap_array.shape[0] != input_shape[0] or shap_array.shape[1] != input_shape[1] or shap_array.shape[2] != input_shape[2]:
        raise ValueError(f"SHAP value shape mismatch: expected {(input_shape[0], input_shape[1], input_shape[2])}, got {shap_array.shape}")
    if np.isnan(shap_array).any():
        raise ValueError("SHAP values contain NaN values.")
    if np.isinf(shap_array).any():
        raise ValueError("SHAP values contain infinite values.")
    if len(feature_names) != input_shape[2]:
        raise ValueError(f"Feature count mismatch: expected {input_shape[2]}, got {len(feature_names)}")


def compute_global_feature_importance(shap_values: np.ndarray, feature_names: list[str]) -> pd.DataFrame:
    mean_abs = np.mean(np.abs(shap_values), axis=(0, 1))
    if mean_abs.shape[0] != len(feature_names):
        raise ValueError(f"Feature importance length mismatch: expected {len(feature_names)}, got {mean_abs.shape[0]}")

    df = pd.DataFrame({
        "feature": feature_names,
        "mean_absolute_shap": mean_abs.astype(float),
    })
    df = df.sort_values("mean_absolute_shap", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", np.arange(1, len(df) + 1))
    return df


def compute_timestep_importance(shap_values: np.ndarray) -> pd.DataFrame:
    mean_abs = np.mean(np.abs(shap_values), axis=(0, 2))
    if mean_abs.shape[0] != 12:
        raise ValueError(f"Timestep importance length mismatch: expected 12, got {mean_abs.shape[0]}")

    values = []
    for timestep_index in range(12):
        values.append({
            "timestep": timestep_index + 1,
            "mean_absolute_shap": float(np.mean(mean_abs[timestep_index])),
        })
    return pd.DataFrame(values)


def create_feature_importance_plot(feature_df: pd.DataFrame, output_path: Path) -> None:
    if plt is None:
        return

    top_20 = feature_df.head(20).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.barh(top_20["feature"], top_20["mean_absolute_shap"])
    ax.invert_yaxis()
    ax.set_title("Experiment 2 LSTM — SHAP Feature Importance")
    ax.set_xlabel("Mean absolute SHAP")
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
        raise ValueError("Normalization statistics do not match the expected feature count.")

    X_train, y_train = load_memmap_split("train")
    verify_split(X_train, y_train, "train", sequence_length, feature_count)

    X_test, y_test = load_memmap_split("test")
    verify_split(X_test, y_test, "test", sequence_length, feature_count)

    background = get_background_data(X_train, train_mean, train_std)
    explanation_X, explanation_y, positive_explanation, negative_explanation, explanation_count = select_explanation_subset(X_test, y_test)
    explanation_X_norm = (explanation_X - train_mean) / train_std

    if background.shape[0] > BACKGROUND_SAMPLES:
        raise ValueError(f"Background sample count exceeds limit: {background.shape[0]} > {BACKGROUND_SAMPLES}")
    if explanation_count > EXPLANATION_SAMPLES:
        raise ValueError(f"Explanation sample count exceeds limit: {explanation_count} > {EXPLANATION_SAMPLES}")

    model = tf.keras.models.load_model(MODEL_PATH)
    input_shape = model.input_shape
    flattened_input_shape = tuple(int(value) for value in input_shape[1:]) if isinstance(input_shape, (list, tuple)) and len(input_shape) > 1 else None
    if flattened_input_shape is None:
        raise ValueError("Could not determine the model input shape.")
    if flattened_input_shape != (12, 76):
        raise ValueError(f"Unexpected model input shape: {flattened_input_shape}; expected (12, 76)")

    model_prob = model.predict(explanation_X_norm, batch_size=256, verbose=0).reshape(-1)
    pred_pos = int(np.sum(model_prob >= THRESHOLD))
    pred_neg = int(np.sum(model_prob < THRESHOLD))
    mean_prob = float(np.mean(model_prob))
    min_prob = float(np.min(model_prob))
    max_prob = float(np.max(model_prob))

    explainer = shap.GradientExplainer(model, background)
    shap_values = explainer.shap_values(explanation_X_norm, nsamples=50)

    shap_array = np.asarray(shap_values)
    if isinstance(shap_values, list):
        if len(shap_values) != 1:
            raise ValueError(f"Unsupported SHAP output structure: list of length {len(shap_values)}")
        shap_array = np.asarray(shap_values[0])
    else:
        shap_array = np.asarray(shap_values)

    if shap_array.ndim == 4:
        if shap_array.shape[-1] != 1:
            raise ValueError(f"Unsupported SHAP output shape: {shap_array.shape}")
        shap_array = shap_array[..., 0]

    if shap_array.ndim == 2:
        if shap_array.shape != (explanation_count * sequence_length, feature_count):
            raise ValueError(f"Unsupported SHAP output shape: {shap_array.shape}")
        shap_array = shap_array.reshape(explanation_count, sequence_length, feature_count)

    if shap_array.shape != (explanation_count, sequence_length, feature_count):
        raise ValueError(f"SHAP values do not match model input dimensions: expected {(explanation_count, sequence_length, feature_count)}, got {shap_array.shape}")

    validate_shap_values(shap_array, (explanation_count, sequence_length, feature_count), feature_names)

    feature_importance = compute_global_feature_importance(shap_array, feature_names)
    timestep_importance = compute_timestep_importance(shap_array)

    positive_subgroup = None
    negative_subgroup = None
    if positive_explanation >= 1 and negative_explanation >= 1:
        pos_mask = explanation_y == 1
        neg_mask = explanation_y == 0
        positive_subgroup = compute_global_feature_importance(shap_array[pos_mask], feature_names)
        negative_subgroup = compute_global_feature_importance(shap_array[neg_mask], feature_names)

    feature_importance.to_csv(MODEL_ROOT / "lstm_shap_feature_importance.csv", index=False)
    timestep_importance.to_csv(MODEL_ROOT / "lstm_shap_timestep_importance.csv", index=False)

    analysis_payload = {
        "model_path": str(MODEL_PATH.relative_to(REPO_ROOT)),
        "normalization_stats_path": str(NORMALIZATION_STATS_PATH.relative_to(REPO_ROOT)),
        "background_sample_count": int(background.shape[0]),
        "explanation_sample_count": int(explanation_count),
        "positive_explanation_sample_count": int(positive_explanation),
        "negative_explanation_sample_count": int(negative_explanation),
        "model_input_shape": [int(sequence_length), int(feature_count)],
        "shap_value_shape": list(shap_array.shape),
        "threshold": float(THRESHOLD),
        "prediction_summary": {
            "predicted_positive": int(pred_pos),
            "predicted_negative": int(pred_neg),
            "mean_probability": float(mean_prob),
            "minimum_probability": float(min_prob),
            "maximum_probability": float(max_prob),
        },
        "top_feature_importance": feature_importance.head(20).to_dict(orient="records"),
        "timestep_importance": timestep_importance.to_dict(orient="records"),
        "positive_subgroup_importance": positive_subgroup.head(20).to_dict(orient="records") if positive_subgroup is not None else None,
        "negative_subgroup_importance": negative_subgroup.head(20).to_dict(orient="records") if negative_subgroup is not None else None,
    }
    with (MODEL_ROOT / "lstm_shap_analysis.json").open("w", encoding="utf-8") as handle:
        json.dump(analysis_payload, handle, indent=2)

    if plt is not None:
        create_feature_importance_plot(feature_importance, MODEL_ROOT / "lstm_shap_feature_importance.png")

    print("SHAP ANALYSIS — EXPERIMENT 2")
    print("MODEL:")
    print(f"  model: {MODEL_PATH.name}")
    print(f"  input shape: {(sequence_length, feature_count)}")

    print("\nSAMPLES:")
    print(f"  background: {background.shape[0]}")
    print(f"  explanation: {explanation_count}")
    print(f"  positive: {positive_explanation}")
    print(f"  negative: {negative_explanation}")

    print("\nPREDICTIONS:")
    print(f"  mean probability: {mean_prob:.6f}")
    print(f"  minimum: {min_prob:.6f}")
    print(f"  maximum: {max_prob:.6f}")
    print(f"  predicted positive: {pred_pos}")
    print(f"  predicted negative: {pred_neg}")

    print("\nSHAP:")
    print(f"  SHAP shape: {shap_array.shape}")
    print(f"  NaN count: {int(np.isnan(shap_array).sum())}")
    print(f"  Inf count: {int(np.isinf(shap_array).sum())}")

    print("\nTOP 20 FEATURES:")
    for idx, row in feature_importance.head(20).iterrows():
        print(f"  {idx + 1}. {row['feature']} = {row['mean_absolute_shap']:.6f}")

    print("\nTIMESTEP IMPORTANCE:")
    for _, row in timestep_importance.iterrows():
        print(f"  {int(row['timestep'])}: {float(row['mean_absolute_shap']):.6f}")

    print("\nFINAL SUMMARY: PASS")


if __name__ == "__main__":
    main()
