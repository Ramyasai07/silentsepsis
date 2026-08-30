"""Validation metrics and validation-only operating-threshold selection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    precision_recall_curve,
    recall_score,
    roc_auc_score,
)


@dataclass(frozen=True)
class ThresholdSelection:
    threshold: float
    validation_f1: float


def select_threshold(y_true: np.ndarray, probabilities: np.ndarray) -> ThresholdSelection:
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    f1_scores = np.divide(
        2 * precision[:-1] * recall[:-1],
        precision[:-1] + recall[:-1],
        out=np.zeros_like(precision[:-1]),
        where=(precision[:-1] + recall[:-1]) != 0,
    )
    best_index = int(np.argmax(f1_scores))
    return ThresholdSelection(float(thresholds[best_index]), float(f1_scores[best_index]))


def evaluate_probabilities(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, object]:
    predictions = probabilities >= threshold
    matrix = confusion_matrix(y_true, predictions, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    specificity = float(tn / (tn + fp)) if tn + fp else 0.0
    calibration_fraction, calibration_mean = calibration_curve(
        y_true,
        probabilities,
        n_bins=10,
        strategy="quantile",
    )

    return {
        "pr_auc": float(average_precision_score(y_true, probabilities)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "specificity": specificity,
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "confusion_matrix": matrix.tolist(),
        "brier_score": float(brier_score_loss(y_true, probabilities)),
        "calibration": {
            "fraction_of_positives": calibration_fraction.tolist(),
            "mean_predicted_value": calibration_mean.tolist(),
            "bins": 10,
            "strategy": "quantile",
        },
        "threshold": float(threshold),
        "positive_rate": float(np.mean(y_true)),
        "sample_count": int(len(y_true)),
    }