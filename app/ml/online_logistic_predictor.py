from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.ml.base import (
    RISK_TIER_CRITICAL,
    RISK_TIER_HIGH,
    RISK_TIER_LOW,
    RISK_TIER_MODERATE,
    FeatureContribution,
    PredictionResult,
    RiskPredictor,
)
from app.models.patient import Gender, Patient
from app.models.patient_baseline import PatientBaseline
from app.models.vital_reading import VitalReading

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = PROJECT_ROOT / "ai" / "artifacts" / "online-logistic-v1-calibrated"

MODEL_PATH = ARTIFACT_ROOT / "model.joblib"
IMPUTER_PATH = ARTIFACT_ROOT / "imputer.joblib"
CALIBRATOR_PATH = ARTIFACT_ROOT / "platt_calibrator.joblib"
METADATA_PATH = ARTIFACT_ROOT / "metadata.json"


class OnlineLogisticPredictor(RiskPredictor):
    """Production predictor for the stateless 15-feature online model."""

    MODEL_VERSION = "online-logistic-v1-calibrated"

    def __init__(self) -> None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model artifact not found: {MODEL_PATH}")
        if not IMPUTER_PATH.exists():
            raise FileNotFoundError(f"Imputer artifact not found: {IMPUTER_PATH}")
        if not CALIBRATOR_PATH.exists():
            raise FileNotFoundError(f"Calibrator artifact not found: {CALIBRATOR_PATH}")
        if not METADATA_PATH.exists():
            raise FileNotFoundError(f"Model metadata not found: {METADATA_PATH}")

        self.model = joblib.load(MODEL_PATH)
        self.imputer = joblib.load(IMPUTER_PATH)
        self.calibrator = joblib.load(CALIBRATOR_PATH)

        self.metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

        self.feature_columns = tuple(self.metadata["feature_columns"])
        self.threshold = float(self.metadata["threshold"])

    @staticmethod
    def _gender_value(patient: Patient) -> float:
        if patient.gender == Gender.FEMALE:
            return 0.0
        if patient.gender == Gender.MALE:
            return 1.0
        return -1.0

    @staticmethod
    def _map_value(
        systolic: float | None,
        diastolic: float | None,
    ) -> float | None:
        if systolic is None or diastolic is None:
            return None
        return (float(systolic) + 2.0 * float(diastolic)) / 3.0

    def _build_features(
        self,
        vitals: VitalReading,
        patient: Patient,
    ) -> pd.DataFrame:
        hr = vitals.heart_rate
        spo2 = vitals.spo2
        temp = vitals.temperature
        sbp = vitals.systolic_bp
        dbp = vitals.diastolic_bp
        resp = vitals.respiratory_rate

        values = {
            "HR": hr,
            "O2Sat": spo2,
            "Temp": temp,
            "SBP": sbp,
            "DBP": dbp,
            "Resp": resp,
            "MAP": self._map_value(sbp, dbp),
            "Age": float(patient.age),
            "Gender": self._gender_value(patient),
            "HR_missing": int(hr is None),
            "O2Sat_missing": int(spo2 is None),
            "Temp_missing": int(temp is None),
            "SBP_missing": int(sbp is None),
            "DBP_missing": int(dbp is None),
            "Resp_missing": int(resp is None),
        }

        frame = pd.DataFrame(
            [[values[column] for column in self.feature_columns]],
            columns=self.feature_columns,
            dtype=np.float32,
        )

        return frame

    def predict(
        self,
        vitals: VitalReading,
        baseline: PatientBaseline | None,
    ) -> PredictionResult:
        baseline_adjustment = 0.0
        if baseline is not None:
            pairs = (
                (vitals.heart_rate, baseline.baseline_hr, 0.20),
                (vitals.spo2, baseline.baseline_spo2, 0.05),
                (vitals.temperature, baseline.baseline_temperature, 0.50),
                (vitals.respiratory_rate, baseline.baseline_rr, 0.50),
                (vitals.systolic_bp, baseline.baseline_systolic_bp, 0.02),
                (vitals.diastolic_bp, baseline.baseline_diastolic_bp, 0.02),
            )
            deviations = [
                abs(float(a) - float(b)) / scale
                for a, b, scale in pairs
                if a is not None and b is not None
            ]
            if deviations:
                baseline_adjustment = min(
                    0.05, sum(deviations) / len(deviations) * 0.01
                )

        patient = vitals.patient
        if patient is None:
            raise ValueError(
                "OnlineLogisticPredictor requires the VitalReading.patient "
                "relationship to be loaded."
            )

        features = self._build_features(vitals, patient)

        imputed = self.imputer.transform(features)

        raw_probability = float(self.model.predict_proba(imputed)[:, 1][0])

        calibrated_probability = float(
            self.calibrator.predict_proba(
                np.asarray([[raw_probability]], dtype=np.float64)
            )[:, 1][0]
        )

        calibrated_probability = float(
            np.clip(calibrated_probability + baseline_adjustment, 0.0, 1.0)
        )

        if calibrated_probability < 0.3:
            risk_tier = RISK_TIER_LOW
        elif calibrated_probability < 0.5:
            risk_tier = RISK_TIER_MODERATE
        elif calibrated_probability < 0.7:
            risk_tier = RISK_TIER_HIGH
        else:
            risk_tier = RISK_TIER_CRITICAL

        contributions = []

        coefficients = self.model.coef_[0]

        for index, column in enumerate(self.feature_columns):
            original_value = features.iloc[0][column]

            if pd.isna(original_value):
                feature_value = None
            else:
                feature_value = float(original_value)

            contribution = float(coefficients[index] * imputed[0][index])

            contributions.append(
                FeatureContribution(
                    feature_name=column,
                    feature_value=feature_value,
                    contribution=contribution,
                )
            )
        if baseline is not None and contributions:
            baseline_features = {
                "HR": baseline.baseline_hr,
                "O2Sat": baseline.baseline_spo2,
                "Temp": baseline.baseline_temperature,
                "Resp": baseline.baseline_rr,
                "SBP": baseline.baseline_systolic_bp,
                "DBP": baseline.baseline_diastolic_bp,
            }
            active_baseline_features = {
                name for name, value in baseline_features.items() if value is not None
            }
            if active_baseline_features:
                adjustment_per_feature = baseline_adjustment / len(
                    active_baseline_features
                )
                contributions = [
                    FeatureContribution(
                        feature_name=item.feature_name,
                        feature_value=item.feature_value,
                        contribution=(
                            item.contribution + adjustment_per_feature
                            if item.feature_name in active_baseline_features
                            else item.contribution
                        ),
                    )
                    for item in contributions
                ]

        contributions.sort(
            key=lambda item: abs(item.contribution),
            reverse=True,
        )

        return PredictionResult(
            risk_score=calibrated_probability,
            risk_tier=risk_tier,
            feature_contributions=contributions,
        )
