#!/usr/bin/env python3
"""Experiment 4: focal-loss LSTM baseline based on the existing Experiment 2 behavior."""

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
from tensorflow import keras

REPO_ROOT = Path(__file__).resolve().parents[2]
SEQUENCE_ROOT = REPO_ROOT / "ai" / "data" / "sequences"
MODEL_ROOT = REPO_ROOT / "ai" / "models"
SEQUENCE_METADATA_PATH = SEQUENCE_ROOT / "sequence_metadata.json"
NORMALIZATION_STATS_PATH = MODEL_ROOT / "lstm_normalization_stats.json"

BATCH_SIZE = 256
MAX_EPOCHS = 20
PATIENCE = 3
THRESHOLD = 0.5
RANDOM_SEED = 42
FOCAL_ALPHA = 0.25
FOCAL_GAMMA = 2.0


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


def verify_sequence_data(
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


def compute_class_counts(y: np.ndarray) -> tuple[int, int]:
    positives = int(np.sum(y == 1))
    negatives = int(np.sum(y == 0))
    return positives, negatives


def make_dataset_from_memmap(
    X: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    train_mean: np.ndarray,
    train_std: np.ndarray,
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
            batch_x = (batch_x - train_mean) / train_std
            yield batch_x, batch_y

    output_signature = (
        tf.TensorSpec(shape=(None, X.shape[1], X.shape[2]), dtype=x_dtype),
        tf.TensorSpec(shape=(None,), dtype=y_dtype),
    )
    return (
        tf.data.Dataset.from_generator(generator, output_signature=output_signature)
        .repeat()
        .prefetch(tf.data.AUTOTUNE)
    )


def binary_focal_loss(
    y_true: tf.Tensor,
    y_pred: tf.Tensor,
    alpha: float = FOCAL_ALPHA,
    gamma: float = FOCAL_GAMMA,
) -> tf.Tensor:
    y_true = tf.cast(y_true, y_pred.dtype)
    y_pred = tf.clip_by_value(
        y_pred,
        tf.keras.backend.epsilon(),
        1.0 - tf.keras.backend.epsilon(),
    )
    p_t = y_true * y_pred + (1.0 - y_true) * (1.0 - y_pred)
    alpha_t = y_true * alpha + (1.0 - y_true) * (1.0 - alpha)
    loss = -alpha_t * tf.pow(1.0 - p_t, gamma) * tf.math.log(p_t)
    return tf.reduce_mean(loss)


def evaluate_predictions(
    y_true: np.ndarray, y_prob: np.ndarray, threshold: float
) -> dict:
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
        loss=binary_focal_loss,
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
    feature_count = int(metadata["number_of_features"])
    train_mean, train_std = load_normalization_stats()

    if train_mean.shape[0] != feature_count or train_std.shape[0] != feature_count:
        raise ValueError(
            "Normalization statistics do not match the expected feature count."
        )

    X_train, y_train = load_split_data("train")
    X_val, y_val = load_split_data("validation")

    verify_sequence_data(X_train, y_train, "train", sequence_length, feature_count)
    verify_sequence_data(X_val, y_val, "validation", sequence_length, feature_count)

    train_positives, train_negatives = compute_class_counts(y_train)
    val_positives, val_negatives = compute_class_counts(y_val)

    train_dataset = make_dataset_from_memmap(
        X_train,
        y_train,
        BATCH_SIZE,
        train_mean,
        train_std,
        shuffle=True,
        seed=RANDOM_SEED,
    )
    val_dataset = make_dataset_from_memmap(
        X_val, y_val, BATCH_SIZE, train_mean, train_std, shuffle=False
    )

    print("EXPERIMENT 4: FOCAL LOSS LSTM")
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

    print("\nNORMALIZATION:")
    print("  statistics source: TRAIN ONLY")

    print("\nFOCAL LOSS:")
    print(f"  alpha: {FOCAL_ALPHA}")
    print(f"  gamma: {FOCAL_GAMMA}")

    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    model = build_model((sequence_length, feature_count))
    model.summary()

    early_stopping = keras.callbacks.EarlyStopping(
        monitor="val_pr_auc",
        mode="max",
        patience=PATIENCE,
        restore_best_weights=True,
    )
    checkpoint_path = MODEL_ROOT / "lstm_experiment4_best.keras"
    model_checkpoint = keras.callbacks.ModelCheckpoint(
        str(checkpoint_path),
        monitor="val_pr_auc",
        mode="max",
        save_best_only=True,
    )

    steps_per_epoch = int(np.ceil(len(y_train) / BATCH_SIZE))
    validation_steps = int(np.ceil(len(y_val) / BATCH_SIZE))

    history = model.fit(
        train_dataset,
        epochs=MAX_EPOCHS,
        steps_per_epoch=steps_per_epoch,
        validation_data=val_dataset,
        validation_steps=validation_steps,
        callbacks=[early_stopping, model_checkpoint],
        verbose=1,
    )

    history_path = MODEL_ROOT / "lstm_experiment4_training_history.json"
    with history_path.open("w", encoding="utf-8") as handle:
        json.dump(history.history, handle, indent=2)

    best_epoch = (
        int(np.argmax(history.history["val_pr_auc"])) + 1
        if "val_pr_auc" in history.history
        else 1
    )
    best_pr_auc = (
        float(np.max(history.history["val_pr_auc"]))
        if "val_pr_auc" in history.history
        else 0.0
    )

    validation_prob = model.predict(
        val_dataset,
        steps=validation_steps,
        verbose=0,
    ).reshape(-1)[: len(y_val)]
    validation_metrics = evaluate_predictions(y_val, validation_prob, THRESHOLD)

    X_test, y_test = load_split_data("test")
    verify_sequence_data(X_test, y_test, "test", sequence_length, feature_count)
    test_positives, test_negatives = compute_class_counts(y_test)

    test_dataset = make_dataset_from_memmap(
        X_test, y_test, BATCH_SIZE, train_mean, train_std, shuffle=False
    )
    test_steps = int(np.ceil(len(y_test) / BATCH_SIZE))
    test_prob = model.predict(
        test_dataset,
        steps=test_steps,
        verbose=0,
    ).reshape(
        -1
    )[: len(y_test)]
    test_metrics = evaluate_predictions(y_test, test_prob, THRESHOLD)

    with (MODEL_ROOT / "lstm_experiment4_evaluation.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(
            {"validation": validation_metrics, "test": test_metrics}, handle, indent=2
        )

    test_df = pd.DataFrame(
        {
            "y_true": y_test.astype(int),
            "y_probability": test_prob.astype(float),
            "y_pred": (test_prob >= THRESHOLD).astype(int),
        }
    )
    test_df.to_csv(MODEL_ROOT / "lstm_experiment4_test_predictions.csv", index=False)

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
