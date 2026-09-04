#!/usr/bin/env python3
"""Read-only threshold analysis for the Experiment 2 normalized LSTM model."""

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

REPO_ROOT = Path(__file__).resolve().parents[2]
SEQUENCE_ROOT = REPO_ROOT / "ai" / "data" / "sequences"
MODEL_ROOT = REPO_ROOT / "ai" / "models"
SEQUENCE_METADATA_PATH = SEQUENCE_ROOT / "sequence_metadata.json"
NORMALIZATION_STATS_PATH = MODEL_ROOT / "lstm_normalization_stats.json"
MODEL_PATH = MODEL_ROOT / "lstm_best.keras"

VALIDATION_THRESHOLDS = [
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
]
BATCH_SIZE = 256


def load_metadata() -> dict:
    with SEQUENCE_METADATA_PATH.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)

    if "sequence_length" not in metadata:
        raise ValueError("sequence_metadata.json is missing sequence_length.")
    if "number_of_features" not in metadata:
        raise ValueError("sequence_metadata.json is missing number_of_features.")

    return metadata


def load_normalization_stats() -> tuple[np.ndarray, np.ndarray, list[str], int, int]:
    if not NORMALIZATION_STATS_PATH.exists():
        raise FileNotFoundError(
            f"Missing normalization stats: {NORMALIZATION_STATS_PATH}"
        )

    with NORMALIZATION_STATS_PATH.open("r", encoding="utf-8") as handle:
        stats = json.load(handle)

    feature_names = list(stats["feature_names"])
    train_mean = np.asarray(stats["means"], dtype=np.float64)
    train_std = np.asarray(stats["standard_deviations"], dtype=np.float64)
    sequence_length = int(stats["sequence_length"])
    number_of_features = int(stats["number_of_features"])

    if train_mean.shape[0] != number_of_features:
        raise ValueError(
            "Normalization stats length does not match number_of_features."
        )
    if train_std.shape[0] != number_of_features:
        raise ValueError("Normalization std length does not match number_of_features.")

    return train_mean, train_std, feature_names, sequence_length, number_of_features


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


def normalize_batch(batch: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return (batch - mean) / std


def predict_probabilities(
    model: tf.keras.Model, X: np.ndarray, mean: np.ndarray, std: np.ndarray
) -> np.ndarray:
    probabilities = []
    num_samples = X.shape[0]

    for start in range(0, num_samples, BATCH_SIZE):
        stop = min(start + BATCH_SIZE, num_samples)
        batch = X[start:stop]
        batch_norm = normalize_batch(batch, mean, std)
        probs = model.predict(batch_norm, verbose=0, batch_size=BATCH_SIZE).reshape(-1)
        probabilities.append(probs)

    return np.concatenate(probabilities, axis=0)


def compute_threshold_metrics(
    y_true: np.ndarray, y_prob: np.ndarray, threshold: float
) -> dict:
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
    }
    return metrics


def evaluate_model(
    model: tf.keras.Model,
    X: np.ndarray,
    y: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
) -> tuple[np.ndarray, dict]:
    probabilities = predict_probabilities(model, X, mean, std)
    metrics = {
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "pr_auc": float(average_precision_score(y, probabilities)),
        "probabilities": probabilities,
    }
    return probabilities, metrics


def main() -> None:
    metadata = load_metadata()
    sequence_length = int(metadata["sequence_length"])
    feature_count = int(metadata["number_of_features"])

    train_mean, train_std, feature_names, _, _ = load_normalization_stats()
    if train_mean.shape[0] != feature_count or train_std.shape[0] != feature_count:
        raise ValueError(
            "Normalization statistics do not match the expected feature count."
        )

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing trained model: {MODEL_PATH}")

    model = tf.keras.models.load_model(MODEL_PATH)

    X_val, y_val = load_memmap_split("validation")
    verify_split(X_val, y_val, "validation", sequence_length, feature_count)

    val_probabilities, _ = evaluate_model(model, X_val, y_val, train_mean, train_std)

    print("LSTM THRESHOLD ANALYSIS")
    print(f"Validation samples: {len(y_val)}")
    print("\nThreshold table:")

    threshold_rows = []
    best_row = None
    best_f1 = -1.0
    best_recall = -1.0

    for threshold in VALIDATION_THRESHOLDS:
        metrics = compute_threshold_metrics(y_val, val_probabilities, threshold)
        threshold_rows.append(metrics)

        print(
            f"  threshold={threshold:.2f} | precision={metrics['precision']:.4f} | recall={metrics['recall']:.4f} | F1={metrics['f1_score']:.4f}"
        )

        if metrics["f1_score"] > best_f1 or (
            np.isclose(metrics["f1_score"], best_f1) and metrics["recall"] > best_recall
        ):
            best_f1 = metrics["f1_score"]
            best_recall = metrics["recall"]
            best_row = metrics

    if best_row is None:
        raise ValueError("No validation threshold could be selected.")

    selected_threshold = float(best_row["threshold"])
    selected_threshold_metrics = compute_threshold_metrics(
        y_val, val_probabilities, selected_threshold
    )

    X_test, y_test = load_memmap_split("test")
    verify_split(X_test, y_test, "test", sequence_length, feature_count)

    test_probabilities, test_threshold_independent = evaluate_model(
        model, X_test, y_test, train_mean, train_std
    )
    test_threshold_metrics = compute_threshold_metrics(
        y_test, test_probabilities, selected_threshold
    )
    experiment2_baseline = compute_threshold_metrics(y_test, test_probabilities, 0.50)

    print(f"Test samples: {len(y_test)}")

    print(f"\nSELECTED THRESHOLD: {selected_threshold:.2f}")
    print(
        f"VALIDATION RESULTS: precision={selected_threshold_metrics['precision']:.4f}, recall={selected_threshold_metrics['recall']:.4f}, F1={selected_threshold_metrics['f1_score']:.4f}"
    )
    print(
        f"TEST RESULTS: threshold={selected_threshold:.2f}, precision={test_threshold_metrics['precision']:.4f}, recall={test_threshold_metrics['recall']:.4f}, F1={test_threshold_metrics['f1_score']:.4f}"
    )

    threshold_df = pd.DataFrame(threshold_rows)
    threshold_df = threshold_df[
        [
            "threshold",
            "true_positives",
            "true_negatives",
            "false_positives",
            "false_negatives",
            "accuracy",
            "precision",
            "recall",
            "f1_score",
        ]
    ]
    threshold_df.to_csv(MODEL_ROOT / "lstm_threshold_results.csv", index=False)

    analysis_payload = {
        "selected_threshold": float(selected_threshold),
        "validation_metrics_at_selected_threshold": selected_threshold_metrics,
        "test_metrics_at_selected_threshold": test_threshold_metrics,
        "threshold_independent_test_roc_auc": float(
            test_threshold_independent["roc_auc"]
        ),
        "threshold_independent_test_pr_auc": float(
            test_threshold_independent["pr_auc"]
        ),
        "experiment2_baseline_threshold": 0.50,
        "experiment2_baseline_test_metrics": experiment2_baseline,
    }
    with (MODEL_ROOT / "lstm_threshold_analysis.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(analysis_payload, handle, indent=2)

    print("\nCOMPARISON")
    print("Experiment 2 threshold 0.50:")
    print(f"  precision={experiment2_baseline['precision']:.4f}")
    print(f"  recall={experiment2_baseline['recall']:.4f}")
    print(f"  F1={experiment2_baseline['f1_score']:.4f}")
    print(f"  ROC-AUC={test_threshold_independent['roc_auc']:.4f}")
    print(f"  PR-AUC={test_threshold_independent['pr_auc']:.4f}")
    print(f"Validation-selected threshold: {selected_threshold:.2f}")
    print(f"  precision={test_threshold_metrics['precision']:.4f}")
    print(f"  recall={test_threshold_metrics['recall']:.4f}")
    print(f"  F1={test_threshold_metrics['f1_score']:.4f}")
    print(f"  ROC-AUC={test_threshold_independent['roc_auc']:.4f}")
    print(f"  PR-AUC={test_threshold_independent['pr_auc']:.4f}")

    print("\nFINAL SUMMARY: PASS")


if __name__ == "__main__":
    main()
