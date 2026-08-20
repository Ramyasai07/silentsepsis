#!/usr/bin/env python3
"""Read-only early-warning analysis for the final Experiment 2 LSTM model.

This script evaluates the existing final Experiment 2 model using the saved test
sequence data and train-only normalization statistics. It intentionally does not
retrain the model, regenerate sequences, or modify any project artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

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

BATCH_SIZE = 256
PRIMARY_THRESHOLD = 0.85
THRESHOLDS = [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90]


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


def load_test_data() -> tuple[np.ndarray, np.ndarray]:
    x_path = SEQUENCE_ROOT / "test_X.npy"
    y_path = SEQUENCE_ROOT / "test_y.npy"

    if not x_path.exists():
        raise FileNotFoundError(f"Missing X array: {x_path}")
    if not y_path.exists():
        raise FileNotFoundError(f"Missing y array: {y_path}")

    X = np.load(x_path, mmap_mode="r", allow_pickle=False)
    y = np.load(y_path, mmap_mode="r", allow_pickle=False)

    if not isinstance(X, np.memmap):
        raise ValueError(f"test: X is not memory-mappable: {type(X)}")
    if not isinstance(y, np.memmap):
        raise ValueError(f"test: y is not memory-mappable: {type(y)}")

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


def predict_probabilities(model: tf.keras.Model, X: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    probabilities = []
    total_samples = X.shape[0]

    for start in range(0, total_samples, BATCH_SIZE):
        stop = min(start + BATCH_SIZE, total_samples)
        batch = X[start:stop]
        batch_norm = (batch - mean) / std
        probs = model.predict(batch_norm, verbose=0, batch_size=BATCH_SIZE).reshape(-1)
        probabilities.append(probs)

    if not probabilities:
        raise ValueError("No probability batches were produced from the test split.")

    return np.concatenate(probabilities, axis=0)


def compute_threshold_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    metrics = {
        "threshold": float(threshold),
        "true_positives": int(tp),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
    }
    return metrics


def summarize_probability_distribution(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    positive_mask = y_true == 1
    negative_mask = y_true == 0

    summary = {
        "total_sequences": int(len(y_true)),
        "positive_sequences": int(np.sum(positive_mask)),
        "negative_sequences": int(np.sum(negative_mask)),
        "positive_percentage": float(np.mean(y_true == 1) * 100.0),
        "positive_mean_probability": float(np.mean(y_prob[positive_mask])) if np.any(positive_mask) else 0.0,
        "negative_mean_probability": float(np.mean(y_prob[negative_mask])) if np.any(negative_mask) else 0.0,
        "positive_median_probability": float(np.median(y_prob[positive_mask])) if np.any(positive_mask) else 0.0,
        "negative_median_probability": float(np.median(y_prob[negative_mask])) if np.any(negative_mask) else 0.0,
        "min_probability": float(np.min(y_prob)),
        "max_probability": float(np.max(y_prob)),
        "predictions_at_or_above_0_85": int(np.sum(y_prob >= 0.85)),
    }
    return summary


def infer_early_warning_availability(metadata: dict) -> dict:
    metadata_keys = {str(key).lower() for key in metadata.keys()}
    required_alignment_fields = {
        "patient_id",
        "start_iculos",
        "end_iculos",
        "target_iculos",
        "target_timestep",
        "patient_sequence_position",
        "sequence_start_iculos",
        "sequence_end_iculos",
    }

    has_alignment_fields = required_alignment_fields.issubset(metadata_keys)

    if has_alignment_fields:
        return {
            "exact_patient_level_lead_time": "AVAILABLE",
            "reason": "The existing metadata contains enough patient/time alignment information to calculate lead time from sequence timing fields.",
            "sequence_metadata_has_required_alignment": True,
        }

    return {
        "exact_patient_level_lead_time": "NOT AVAILABLE FROM CURRENT SEQUENCE ARTIFACTS",
        "reason": (
            "The existing sequence artifacts and metadata do not include patient_id, start/end ICULOS, target timestep, "
            "or patient sequence position. Without those alignment fields, exact patient-level lead time cannot be recovered "
            "without inventing missing timing information."
        ),
        "sequence_metadata_has_required_alignment": False,
    }


def create_probability_distribution_plot(y_prob: np.ndarray, output_path: Path) -> None:
    if plt is None:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(y_prob, bins=30, range=(0.0, 1.0), color="#2f6fed", edgecolor="black")
    ax.axvline(0.85, color="red", linestyle="--", linewidth=1.5, label="0.85 threshold")
    ax.set_title("Experiment 2 Test Sequence Prediction Probability Distribution")
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Sequence count")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    metadata = load_metadata()
    sequence_length = int(metadata["sequence_length"])
    feature_count = int(metadata["number_of_features"])

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing model: {MODEL_PATH}")

    train_mean, train_std = load_normalization_stats()
    if train_mean.shape[0] != feature_count or train_std.shape[0] != feature_count:
        raise ValueError("Normalization statistics do not match the expected feature count.")

    model = tf.keras.models.load_model(MODEL_PATH)
    X_test, y_test = load_test_data()
    verify_split(X_test, y_test, "test", sequence_length, feature_count)

    y_prob = predict_probabilities(model, X_test, train_mean, train_std)
    if y_prob.shape[0] != y_test.shape[0]:
        raise ValueError(f"Prediction count mismatch: expected {y_test.shape[0]}, got {y_prob.shape[0]}")

    test_summary = summarize_probability_distribution(y_test, y_prob)
    final_metrics = compute_threshold_metrics(y_test, y_prob, PRIMARY_THRESHOLD)
    threshold_metrics = []
    for threshold in THRESHOLDS:
        threshold_metrics.append(compute_threshold_metrics(y_test, y_prob, threshold))

    early_warning = infer_early_warning_availability(metadata)

    analysis_payload = {
        "model_path": str(MODEL_PATH.relative_to(REPO_ROOT)),
        "normalization_stats_path": str(NORMALIZATION_STATS_PATH.relative_to(REPO_ROOT)),
        "final_threshold": float(PRIMARY_THRESHOLD),
        "test": {
            "total_sequences": int(test_summary["total_sequences"]),
            "positive_sequences": int(test_summary["positive_sequences"]),
            "negative_sequences": int(test_summary["negative_sequences"]),
            "positive_percentage": float(test_summary["positive_percentage"]),
        },
        "probability_analysis": {
            "positive_mean_probability": float(test_summary["positive_mean_probability"]),
            "negative_mean_probability": float(test_summary["negative_mean_probability"]),
            "positive_median_probability": float(test_summary["positive_median_probability"]),
            "negative_median_probability": float(test_summary["negative_median_probability"]),
            "minimum_probability": float(test_summary["min_probability"]),
            "maximum_probability": float(test_summary["max_probability"]),
            "predictions_at_or_above_0_85": int(test_summary["predictions_at_or_above_0_85"]),
        },
        "final_threshold_metrics": {
            "threshold": float(PRIMARY_THRESHOLD),
            "precision": float(final_metrics["precision"]),
            "recall": float(final_metrics["recall"]),
            "f1_score": float(final_metrics["f1_score"]),
            "accuracy": float(final_metrics["accuracy"]),
            "roc_auc": float(final_metrics["roc_auc"]),
            "pr_auc": float(final_metrics["pr_auc"]),
            "confusion_matrix": [
                int(final_metrics["true_negatives"]),
                int(final_metrics["false_positives"]),
                int(final_metrics["false_negatives"]),
                int(final_metrics["true_positives"]),
            ],
        },
        "threshold_analysis": {str(item["threshold"]): item for item in threshold_metrics},
        "early_warning": early_warning,
    }

    analysis_path = MODEL_ROOT / "lstm_early_warning_analysis.json"
    with analysis_path.open("w", encoding="utf-8") as handle:
        json.dump(analysis_payload, handle, indent=2)

    threshold_rows = []
    for item in threshold_metrics:
        threshold_rows.append(
            {
                "threshold": item["threshold"],
                "true_positives": item["true_positives"],
                "true_negatives": item["true_negatives"],
                "false_positives": item["false_positives"],
                "false_negatives": item["false_negatives"],
                "accuracy": item["accuracy"],
                "precision": item["precision"],
                "recall": item["recall"],
                "f1_score": item["f1_score"],
                "roc_auc": item["roc_auc"],
                "pr_auc": item["pr_auc"],
            }
        )

    threshold_df = pd.DataFrame(threshold_rows)
    threshold_df.to_csv(MODEL_ROOT / "lstm_early_warning_thresholds.csv", index=False)

    plot_path = MODEL_ROOT / "lstm_probability_distribution.png"
    create_probability_distribution_plot(y_prob, plot_path)

    print("EARLY-WARNING ANALYSIS — EXPERIMENT 2")
    print("TEST:")
    print(f"  total sequences: {test_summary['total_sequences']}")
    print(f"  positive: {test_summary['positive_sequences']}")
    print(f"  negative: {test_summary['negative_sequences']}")
    print(f"  positive percentage: {test_summary['positive_percentage']:.2f}%")

    print("\nPROBABILITY ANALYSIS:")
    print(f"  positive mean: {test_summary['positive_mean_probability']:.6f}")
    print(f"  negative mean: {test_summary['negative_mean_probability']:.6f}")
    print(f"  positive median: {test_summary['positive_median_probability']:.6f}")
    print(f"  negative median: {test_summary['negative_median_probability']:.6f}")
    print(f"  minimum: {test_summary['min_probability']:.6f}")
    print(f"  maximum: {test_summary['max_probability']:.6f}")

    print("\nFINAL THRESHOLD:")
    print(f"  threshold: {PRIMARY_THRESHOLD}")
    print(f"  precision: {final_metrics['precision']:.4f}")
    print(f"  recall: {final_metrics['recall']:.4f}")
    print(f"  F1: {final_metrics['f1_score']:.4f}")

    print("\nTHRESHOLD ANALYSIS:")
    for item in threshold_metrics:
        print(f"  {item['threshold']:.2f}: precision={item['precision']:.4f}, recall={item['recall']:.4f}, F1={item['f1_score']:.4f}")

    print("\nEARLY WARNING:")
    print(f"  exact patient-level lead time: {early_warning['exact_patient_level_lead_time']}")
    if not early_warning["sequence_metadata_has_required_alignment"]:
        print("  reason: The existing sequence metadata and arrays do not include patient-level alignment fields needed to recover exact lead time.")

    print("\nFINAL SUMMARY: PASS")


if __name__ == "__main__":
    main()
