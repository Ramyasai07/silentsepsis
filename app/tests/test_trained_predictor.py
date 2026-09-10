import json
from datetime import datetime, timezone

from app.ml.rule_based_predictor import RuleBasedPredictor
from app.ml.trained_predictor import TrainedRiskPredictor
from app.models.patient import Gender, Patient
from app.models.vital_reading import VitalReading


def make_vitals(**values: float) -> VitalReading:
    patient = Patient(age=64, gender=Gender.MALE)
    return VitalReading(
        patient=patient,
        heart_rate=values["heart_rate"],
        respiratory_rate=values["respiratory_rate"],
        systolic_bp=values["systolic_bp"],
        diastolic_bp=values["diastolic_bp"],
        spo2=values["spo2"],
        temperature=values["temperature"],
        recorded_at=datetime.now(timezone.utc),
    )


def test_trained_predictor_is_deterministic_for_identical_input() -> None:
    vitals = make_vitals(
        heart_rate=80,
        respiratory_rate=18,
        systolic_bp=120,
        diastolic_bp=75,
        spo2=98,
        temperature=36.8,
    )
    predictor = TrainedRiskPredictor()

    first = predictor.predict(vitals, None)
    second = predictor.predict(vitals, None)

    assert first == second


def test_trained_predictor_comparison_with_rule_based_baseline() -> None:
    cases = {
        "clearly_stable": {
            "heart_rate": 72,
            "respiratory_rate": 16,
            "systolic_bp": 118,
            "diastolic_bp": 70,
            "spo2": 98,
            "temperature": 36.8,
        },
        "clearly_critical": {
            "heart_rate": 145,
            "respiratory_rate": 32,
            "systolic_bp": 78,
            "diastolic_bp": 45,
            "spo2": 84,
            "temperature": 39.8,
        },
    }
    rule_based = RuleBasedPredictor()
    trained = TrainedRiskPredictor()
    comparison = {}

    for name, values in cases.items():
        vitals = make_vitals(**values)
        rule_result = rule_based.predict(vitals, None)
        trained_result = trained.predict(vitals, None)
        comparison[name] = {
            "rule_based": {
                "risk_score": rule_result.risk_score,
                "risk_tier": rule_result.risk_tier,
            },
            "trained": {
                "risk_score": trained_result.risk_score,
                "risk_tier": trained_result.risk_tier,
            },
        }
        assert 0.0 <= trained_result.risk_score <= 1.0
        assert [
            abs(feature.contribution)
            for feature in trained_result.feature_contributions
        ] == sorted(
            (
                abs(feature.contribution)
                for feature in trained_result.feature_contributions
            ),
            reverse=True,
        )

    print(json.dumps(comparison, indent=2))
