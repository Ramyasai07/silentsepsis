from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from app.ml.base import (
    FeatureContribution,
    PredictionResult,
    RISK_SCORE_HIGH_MAX,
    RISK_SCORE_LOW_MAX,
    RISK_SCORE_MODERATE_MAX,
    RISK_TIER_CRITICAL,
    RISK_TIER_HIGH,
    RISK_TIER_LOW,
    RISK_TIER_MODERATE,
    RiskPredictor,
)
from app.models.patient_baseline import PatientBaseline
from app.models.vital_reading import VitalReading

NORMAL_HR_RANGE = (60.0, 100.0)
NORMAL_RR_RANGE = (12.0, 20.0)
NORMAL_SPO2 = 95.0
NORMAL_TEMPERATURE_RANGE = (36.1, 37.2)
NORMAL_SYSTOLIC_BP_RANGE = (90.0, 120.0)
NORMAL_DIASTOLIC_BP_RANGE = (60.0, 80.0)

HR_WEIGHT = 1.0
RR_WEIGHT = 1.6
SPO2_WEIGHT = 1.8
TEMPERATURE_WEIGHT = 0.8
SYSTOLIC_BP_WEIGHT = 1.0
DIASTOLIC_BP_WEIGHT = 1.0
MAX_RISK_SCORE = HR_WEIGHT + RR_WEIGHT + SPO2_WEIGHT + TEMPERATURE_WEIGHT + SYSTOLIC_BP_WEIGHT + DIASTOLIC_BP_WEIGHT


def _mean(range_tuple: tuple[float, float]) -> float:
    return (range_tuple[0] + range_tuple[1]) / 2.0


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _normalize_signed_deviation(value: float, target: float, scale: float) -> float:
    return _clamp((value - target) / scale, -1.0, 1.0)


def _normalize_unsigned_deviation(value: float, target: float, scale: float) -> float:
    return _clamp(abs(value - target) / scale, 0.0, 1.0)


def _baseline_or_normal(value: float | None, normal: float | tuple[float, float]) -> float:
    if value is not None:
        return value
    if isinstance(normal, tuple):
        return _mean(normal)
    return normal


def _risk_tier(score: float) -> str:
    if score < RISK_SCORE_LOW_MAX:
        return RISK_TIER_LOW
    if score < RISK_SCORE_MODERATE_MAX:
        return RISK_TIER_MODERATE
    if score < RISK_SCORE_HIGH_MAX:
        return RISK_TIER_HIGH
    return RISK_TIER_CRITICAL


class RuleBasedPredictor(RiskPredictor):
    """A deterministic rule-based stand-in for the production risk predictor.

    This implementation is not a final clinical model. It exists to establish the
    prediction pipeline and feature-attribution interface. A future trained model
    can replace it without changing the API, service, or persistence layers.
    """

    def predict(
        self,
        vitals: VitalReading,
        baseline: PatientBaseline | None,
    ) -> PredictionResult:
        hr_target = _baseline_or_normal(
            baseline.baseline_hr if baseline is not None else None,
            NORMAL_HR_RANGE,
        )
        rr_target = _baseline_or_normal(
            baseline.baseline_rr if baseline is not None else None,
            NORMAL_RR_RANGE,
        )
        spo2_target = _baseline_or_normal(
            baseline.baseline_spo2 if baseline is not None else None,
            NORMAL_SPO2,
        )
        temperature_target = _baseline_or_normal(
            baseline.baseline_temperature if baseline is not None else None,
            NORMAL_TEMPERATURE_RANGE,
        )
        systolic_bp_target = _baseline_or_normal(
            baseline.baseline_systolic_bp if baseline is not None else None,
            NORMAL_SYSTOLIC_BP_RANGE,
        )
        diastolic_bp_target = _baseline_or_normal(
            baseline.baseline_diastolic_bp if baseline is not None else None,
            NORMAL_DIASTOLIC_BP_RANGE,
        )

        hr_contribution = _normalize_signed_deviation(
            vitals.heart_rate,
            hr_target,
            max(NORMAL_HR_RANGE[1] - NORMAL_HR_RANGE[0], 1.0),
        )
        rr_contribution = _normalize_signed_deviation(
            vitals.respiratory_rate,
            rr_target,
            max(NORMAL_RR_RANGE[1] - NORMAL_RR_RANGE[0], 1.0),
        )
        spo2_contribution = _clamp(
            (spo2_target - vitals.spo2) / max(spo2_target, 1.0),
            -1.0,
            1.0,
        )
        temperature_contribution = _normalize_signed_deviation(
            vitals.temperature,
            temperature_target,
            max(NORMAL_TEMPERATURE_RANGE[1] - NORMAL_TEMPERATURE_RANGE[0], 0.1),
        )
        systolic_bp_contribution = _clamp(
            (systolic_bp_target - vitals.systolic_bp) / max(systolic_bp_target, 1.0),
            -1.0,
            1.0,
        )
        diastolic_bp_contribution = _clamp(
            (diastolic_bp_target - vitals.diastolic_bp) / max(diastolic_bp_target, 1.0),
            -1.0,
            1.0,
        )

        weighted_contributions = [
            FeatureContribution(
                feature_name="heart_rate",
                contribution=hr_contribution * HR_WEIGHT,
                feature_value=vitals.heart_rate,
            ),
            FeatureContribution(
                feature_name="respiratory_rate",
                contribution=rr_contribution * RR_WEIGHT,
                feature_value=vitals.respiratory_rate,
            ),
            FeatureContribution(
                feature_name="spo2",
                contribution=spo2_contribution * SPO2_WEIGHT,
                feature_value=vitals.spo2,
            ),
            FeatureContribution(
                feature_name="temperature",
                contribution=temperature_contribution * TEMPERATURE_WEIGHT,
                feature_value=vitals.temperature,
            ),
            FeatureContribution(
                feature_name="systolic_bp",
                contribution=systolic_bp_contribution * SYSTOLIC_BP_WEIGHT,
                feature_value=vitals.systolic_bp,
            ),
            FeatureContribution(
                feature_name="diastolic_bp",
                contribution=diastolic_bp_contribution * DIASTOLIC_BP_WEIGHT,
                feature_value=vitals.diastolic_bp,
            ),
        ]

        total_score = sum(fc.contribution for fc in weighted_contributions)
        normalized_score = _clamp(total_score / MAX_RISK_SCORE, 0.0, 1.0)
        risk_tier = _risk_tier(normalized_score)

        sorted_contributions = sorted(
            weighted_contributions,
            key=lambda item: abs(item.contribution),
            reverse=True,
        )

        return PredictionResult(
            risk_score=normalized_score,
            risk_tier=risk_tier,
            feature_contributions=sorted_contributions,
        )
