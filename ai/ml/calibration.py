"""Validation-only calibration helpers for trained probability models."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression


def probability_logits(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped))


def fit_platt_calibrator(
    probabilities: np.ndarray,
    targets: np.ndarray,
) -> LogisticRegression:
    calibrator = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
    calibrator.fit(probability_logits(probabilities).reshape(-1, 1), targets)
    return calibrator


def calibrate_probabilities(
    calibrator: LogisticRegression,
    probabilities: np.ndarray,
) -> np.ndarray:
    logits = probability_logits(probabilities).reshape(-1, 1)
    return calibrator.predict_proba(logits)[:, 1]