import numpy as np
import pytest

from ai.ml.metrics import evaluate_probabilities, select_threshold


def test_select_threshold_uses_validation_probabilities() -> None:
    result = select_threshold(
        np.array([0, 0, 1, 1]),
        np.array([0.1, 0.2, 0.8, 0.9]),
    )

    assert result.threshold == 0.8
    assert result.validation_f1 == 1.0


def test_evaluate_probabilities_reports_requested_metrics() -> None:
    metrics = evaluate_probabilities(
        np.array([0, 0, 1, 1]),
        np.array([0.1, 0.2, 0.8, 0.9]),
        threshold=0.5,
    )

    assert metrics["pr_auc"] == 1.0
    assert metrics["roc_auc"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["specificity"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["confusion_matrix"] == [[2, 0], [0, 2]]
    assert metrics["brier_score"] == pytest.approx(0.025)
    assert set(metrics["calibration"]) == {
        "fraction_of_positives",
        "mean_predicted_value",
        "bins",
        "strategy",
    }