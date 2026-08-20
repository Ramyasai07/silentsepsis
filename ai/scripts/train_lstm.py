#!/usr/bin/env python3
"""Baseline LSTM training pipeline for the SilentSepsis sequence data.

This script loads the already-generated sequence datasets and trains a simple
LSTM baseline. It does not regenerate sequences, does not modify project data,
and does not touch any non-AI files.
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
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from tensorflow import keras

REPO_ROOT = Path(__file__).resolve().parents[2]
SEQUENCE_ROOT = REPO_ROOT / "ai" / "data" / "sequences"
MODEL_ROOT = REPO_ROOT / "ai" / "models"
SEQUENCE_METADATA_PATH = SEQUENCE_ROOT / "sequence_metadata.json"

BATCH_SIZE = 256
MAX_EPOCHS = 20
PATIENCE = 3
THRESHOLD = 0.5
RANDOM_SEED = 42


def set_random_seeds() -> None:
    np.random.seed(RANDOM_SEED)
    tf.random.set_seed(RANDOM_SEED)


def load_metadata() -> dict:
    if not SEQUENCE_METADATA_PATH.exists():
        raise FileNotFoundError(f"Missing sequence metadata: {SEQUENCE_METADATA_PATH}")

    with SEQUENCE_METADATA_PATH.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)

    if "sequence_length" not in metadata:
        raise ValueError("sequence_metadata.json is missing sequence_length.")
    if "feature_names" not in metadata:
        raise ValueError("sequence_metadata.json is missing feature_names.")
    if "number_of_features" not in metadata:
        raise ValueError("sequence_metadata.json is missing number_of_features.")

    return metadata


def load_split_data(split_name: str) -> tuple[np.ndarray, np.ndarray]:
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


def verify_sequence_data(X: np.ndarray, y: np.ndarray, split_name: str, sequence_length: int, feature_count: int) -> None:
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


def compute_training_statistics(X_train: np.ndarray, feature_count: int) -> tuple[np.ndarray, np.ndarray, int]:
    count = 0
    feature_sums = np.zeros(feature_count, dtype=np.float64)
    feature_sumsq = np.zeros(feature_count, dtype=np.float64)

    chunk_size = 8192
    for start in range(0, X_train.shape[0], chunk_size):
        stop = min(start + chunk_size, X_train.shape[0])
        chunk = X_train[start:stop]
        chunk_flat = chunk.reshape(-1, feature_count)
        feature_sums += chunk_flat.sum(axis=0)
        feature_sumsq += np.square(chunk_flat).sum(axis=0)
        count += chunk_flat.shape[0]

    if count == 0:
        raise ValueError("Training data is empty; cannot compute normalization statistics.")

    means = feature_sums / count
    variances = feature_sumsq / count - np.square(means)
    stds = np.sqrt(np.clip(variances, 0.0, None))
    zero_variance = stds == 0.0
    zero_variance_count = int(np.sum(zero_variance))

    if np.any(zero_variance):
        stds[zero_variance] = 1.0

    return means, stds, zero_variance_count


def save_normalization_stats(feature_names: list[str], means: np.ndarray, stds: np.ndarray, sequence_length: int, feature_count: int) -> None:
    stats_path = MODEL_ROOT / "lstm_normalization_stats.json"
    payload = {
        "feature_names": feature_names,
        "means": [float(value) for value in means.tolist()],
        "standard_deviations": [float(value) for value in stds.tolist()],
        "sequence_length": int(sequence_length),
        "number_of_features": int(feature_count),
    }
    with stats_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def calculate_class_weights(y_train: np.ndarray) -> dict[int, float]:
    positive = int(np.sum(y_train == 1))
    negative = int(np.sum(y_train == 0))
    if positive == 0 or negative == 0:
        raise ValueError(f"Training labels must contain both classes. Positive={positive}, Negative={negative}")

    total = positive + negative
    weight_for_zero = total / (2.0 * negative)
    weight_for_one = total / (2.0 * positive)
    return {0: float(weight_for_zero), 1: float(weight_for_one)}


def make_dataset_from_memmap(
    X: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    train_mean: np.ndarray | None = None,
    train_std: np.ndarray | None = None,
    shuffle: bool = False,
    seed: int = RANDOM_SEED,
) -> tf.data.Dataset:
    num_samples = int(X.shape[0])
    x_dtype = tf.as_dtype(X.dtype)
    y_dtype = tf.as_dtype(y.dtype)

    if shuffle:
        order = np.arange(num_samples)
        rng = np.random.default_rng(seed)
        order = rng.permutation(order)
    else:
        order = np.arange(num_samples)

    def generator():
        for start in range(0, len(order), batch_size):
            stop = min(start + batch_size, len(order))
            batch_idx = order[start:stop]
            batch_x = X[batch_idx]
            batch_y = y[batch_idx]

            if train_mean is not None and train_std is not None:
                batch_x = (batch_x - train_mean) / train_std

            yield batch_x, batch_y

    output_signature = (
        tf.TensorSpec(shape=(None, X.shape[1], X.shape[2]), dtype=x_dtype),
        tf.TensorSpec(shape=(None,), dtype=y_dtype),
    )
    return tf.data.Dataset.from_generator(generator, output_signature=output_signature).prefetch(tf.data.AUTOTUNE)


def compute_class_counts(y: np.ndarray) -> tuple[int, int]:
    positives = int(np.sum(y == 1))
    negatives = int(np.sum(y == 0))
    return positives, negatives


def evaluate_predictions(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_true, y_prob)
    pr_auc = average_precision_score(y_true, y_prob)

    return {
        "confusion_matrix": [int(tn), int(fp), int(fn), int(tp)],
        "true_positives": int(tp),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
    }


def build_model(input_shape: tuple[int, int]) -> keras.Model:
    model = keras.Sequential(
        [
            keras.layers.Input(shape=input_shape),
            keras.layers.LSTM(64),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(32, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(
        optimizer=keras.optimizers.Adam(),
        loss="binary_crossentropy",
        metrics=[
            keras.metrics.Precision(name="precision"),
            keras.metrics.Recall(name="recall"),
            keras.metrics.AUC(name="auc", curve="ROC"),
            keras.metrics.AUC(name="pr_auc", curve="PR"),
        ],
    )
    return model


def main() -> None:
    set_random_seeds()
    metadata = load_metadata()
    sequence_length = int(metadata["sequence_length"])
    feature_names = list(metadata["feature_names"])
    feature_count = int(metadata["number_of_features"])

    X_train, y_train = load_split_data("train")
    X_val, y_val = load_split_data("validation")
    X_test, y_test = load_split_data("test")

    verify_sequence_data(X_train, y_train, "train", sequence_length, feature_count)
    verify_sequence_data(X_val, y_val, "validation", sequence_length, feature_count)
    verify_sequence_data(X_test, y_test, "test", sequence_length, feature_count)

    if X_train.shape[2] != feature_count or X_val.shape[2] != feature_count or X_test.shape[2] != feature_count:
        raise ValueError("Sequence feature counts are not consistent with metadata.")

    if X_train.shape[1] != sequence_length or X_val.shape[1] != sequence_length or X_test.shape[1] != sequence_length:
        raise ValueError("Sequence lengths are not consistent across splits.")

    for split_name, y in {"train": y_train, "validation": y_val, "test": y_test}.items():
        positives, negatives = compute_class_counts(y)
        if positives == 0 or negatives == 0:
            raise ValueError(f"{split_name}: positive class is missing or negative class is missing.")

    train_positives, train_negatives = compute_class_counts(y_train)
    val_positives, val_negatives = compute_class_counts(y_val)
    test_positives, test_negatives = compute_class_counts(y_test)

    train_mean, train_std, zero_variance_features = compute_training_statistics(X_train, feature_count)
    save_normalization_stats(feature_names, train_mean, train_std, sequence_length, feature_count)

    train_dataset = make_dataset_from_memmap(X_train, y_train, BATCH_SIZE, train_mean, train_std, shuffle=True, seed=RANDOM_SEED)
    val_dataset = make_dataset_from_memmap(X_val, y_val, BATCH_SIZE, train_mean, train_std, shuffle=False)
    test_dataset = make_dataset_from_memmap(X_test, y_test, BATCH_SIZE, train_mean, train_std, shuffle=False)

    print("EXPERIMENT 2: NORMALIZED LSTM")
    print("TRAIN:")
    print(f"  X shape: {X_train.shape}")
    print(f"  y shape: {y_train.shape}")
    print(f"  positive: {train_positives}")
    print(f"  negative: {train_negatives}")
    print(f"  positive percentage: {100.0 * train_positives / len(y_train):.2f}%")

    print("\nVALIDATION:")
    print(f"  X shape: {X_val.shape}")
    print(f"  y shape: {y_val.shape}")
    print(f"  positive: {val_positives}")
    print(f"  negative: {val_negatives}")
    print(f"  positive percentage: {100.0 * val_positives / len(y_val):.2f}%")

    print("\nTEST:")
    print(f"  X shape: {X_test.shape}")
    print(f"  y shape: {y_test.shape}")
    print(f"  positive: {test_positives}")
    print(f"  negative: {test_negatives}")
    print(f"  positive percentage: {100.0 * test_positives / len(y_test):.2f}%")

    print("\nNORMALIZATION:")
    print("  statistics source: TRAIN ONLY")
    print(f"  number of features: {feature_count}")
    print(f"  zero-variance features: {zero_variance_features}")

    class_weights = calculate_class_weights(y_train)
    print("\nCLASS WEIGHTS:")
    print(class_weights)

    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    model = build_model((sequence_length, feature_count))
    model.summary()

    early_stopping = keras.callbacks.EarlyStopping(
        monitor="val_pr_auc",
        mode="max",
        patience=PATIENCE,
        restore_best_weights=True,
    )
    model_checkpoint = keras.callbacks.ModelCheckpoint(
        str(MODEL_ROOT / "lstm_best.keras"),
        monitor="val_pr_auc",
        mode="max",
        save_best_only=True,
    )

    history = model.fit(
        train_dataset,
        epochs=MAX_EPOCHS,
        validation_data=val_dataset,
        class_weight=class_weights,
        callbacks=[early_stopping, model_checkpoint],
        verbose=1,
    )

    history_path = MODEL_ROOT / "lstm_training_history.json"
    with history_path.open("w", encoding="utf-8") as handle:
        json.dump(history.history, handle, indent=2)

    best_epoch = int(np.argmax(history.history["val_pr_auc"])) + 1 if "val_pr_auc" in history.history else 1
    best_pr_auc = float(np.max(history.history["val_pr_auc"])) if "val_pr_auc" in history.history else 0.0

    validation_prob = model.predict(val_dataset, verbose=0).reshape(-1)
    test_prob = model.predict(test_dataset, verbose=0).reshape(-1)

    validation_metrics = evaluate_predictions(y_val, validation_prob, THRESHOLD)
    test_metrics = evaluate_predictions(y_test, test_prob, THRESHOLD)

    with (MODEL_ROOT / "lstm_evaluation.json").open("w", encoding="utf-8") as handle:
        json.dump({"validation": validation_metrics, "test": test_metrics}, handle, indent=2)

    test_df = pd.DataFrame(
        {
            "y_true": y_test.astype(int),
            "y_probability": test_prob.astype(float),
            "y_pred": (test_prob >= THRESHOLD).astype(int),
        }
    )
    test_df.to_csv(MODEL_ROOT / "lstm_test_predictions.csv", index=False)

    print("\nTRAINING COMPLETE")
    print(f"Best epoch: {best_epoch}")
    print(f"Best validation PR-AUC: {best_pr_auc:.6f}")

    print("\nVALIDATION RESULTS")
    for key, value in validation_metrics.items():
        print(f"  {key}: {value}")

    print("\nTEST RESULTS")
    for key, value in test_metrics.items():
        print(f"  {key}: {value}")

    print("\nFINAL SUMMARY: PASS")


if __name__ == "__main__":
    main()
