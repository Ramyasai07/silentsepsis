import pandas as pd
from sepsis_ai.features.trend_features import (
    BASELINE_WINDOW_HOURS,
    engineer_patient_features,
)


def test_baseline_and_deviation():
    patient = pd.DataFrame(
        {
            "patient_id": ["p1"] * 5,
            "ICULOS": [0, 1, 2, 3, 4],
            "HR": [70, 72, 74, 80, 85],
            "Resp": [16, 16, 18, 18, 19],
            "O2Sat": [98, 98, 97, 96, 95],
            "Temp": [36.8, 36.9, 37.0, 37.1, 37.3],
            "SBP": [120, 118, 115, 110, 108],
            "DBP": [80, 78, 75, 72, 70],
            "target": [0, 0, 0, 1, 1],
        }
    )

    result = engineer_patient_features(patient)
    assert (
        result["heart_rate_baseline"].iloc[0] == result["heart_rate_baseline"].iloc[1]
    )
    assert result["heart_rate_deviation"].iloc[-1] > 0
    assert result["heart_rate_pct_deviation"].iloc[-1] > 0


def test_first_difference():
    patient = pd.DataFrame(
        {
            "patient_id": ["p1"] * 4,
            "ICULOS": [0, 1, 2, 3],
            "HR": [80, 83, 89, 94],
            "Resp": [18, 18, 20, 22],
            "O2Sat": [97, 97, 96, 95],
            "Temp": [36.7, 36.8, 37.0, 37.3],
            "SBP": [120, 118, 112, 108],
            "DBP": [80, 75, 71, 68],
            "target": [0, 0, 1, 1],
        }
    )
    result = engineer_patient_features(patient)
    assert result["heart_rate_delta"].iloc[0] == 0.0
    assert result["heart_rate_delta"].iloc[1] == 3.0
    assert result["heart_rate_delta"].iloc[2] == 6.0


def test_rolling_mean_and_std():
    patient = pd.DataFrame(
        {
            "patient_id": ["p1"] * 4,
            "ICULOS": [0, 1, 2, 3],
            "HR": [70, 75, 85, 95],
            "Resp": [16, 17, 18, 19],
            "O2Sat": [98, 97, 96, 95],
            "Temp": [36.8, 36.9, 37.1, 37.3],
            "SBP": [120, 118, 110, 102],
            "DBP": [80, 78, 72, 66],
            "target": [0, 0, 1, 1],
        }
    )
    result = engineer_patient_features(patient)
    assert result["heart_rate_rolling_mean"].iloc[0] == 70.0
    assert result["heart_rate_rolling_mean"].iloc[1] == 72.5
    assert result["heart_rate_rolling_std"].iloc[0] == 0.0
    assert result["heart_rate_rolling_std"].iloc[1] == 2.5


def test_patient_boundary_isolation():
    patient_a = pd.DataFrame(
        {
            "patient_id": ["a"] * 3,
            "ICULOS": [0, 1, 2],
            "HR": [70, 80, 90],
            "Resp": [16, 18, 20],
            "O2Sat": [98, 97, 96],
            "Temp": [36.8, 36.9, 37.0],
            "SBP": [120, 120, 110],
            "DBP": [80, 80, 70],
            "target": [0, 0, 1],
        }
    )
    patient_b = pd.DataFrame(
        {
            "patient_id": ["b"] * 3,
            "ICULOS": [0, 1, 2],
            "HR": [60, 62, 64],
            "Resp": [14, 15, 15],
            "O2Sat": [99, 99, 98],
            "Temp": [36.5, 36.6, 36.7],
            "SBP": [110, 112, 114],
            "DBP": [72, 73, 74],
            "target": [0, 0, 0],
        }
    )
    table = pd.concat(
        [engineer_patient_features(patient_a), engineer_patient_features(patient_b)],
        ignore_index=True,
    )
    assert table.loc[table["patient_id"] == "a", "heart_rate_delta"].tolist() == [
        0.0,
        10.0,
        10.0,
    ]
    assert table.loc[table["patient_id"] == "b", "heart_rate_delta"].tolist() == [
        0.0,
        2.0,
        2.0,
    ]


def test_zero_baseline_protection():
    patient = pd.DataFrame(
        {
            "patient_id": ["p1"] * 3,
            "ICULOS": [0, 1, 2],
            "HR": [0, 0, 0],
            "Resp": [0, 0, 0],
            "O2Sat": [0, 0, 0],
            "Temp": [0, 0, 0],
            "SBP": [0, 0, 0],
            "DBP": [0, 0, 0],
            "target": [0, 0, 0],
        }
    )
    result = engineer_patient_features(patient)
    assert (result["heart_rate_pct_deviation"] == 0.0).all()
    assert (result["shock_index"] == 0.0).all()


def test_shock_index_invalid_sbp_protection():
    patient = pd.DataFrame(
        {
            "patient_id": ["p1"] * 3,
            "ICULOS": [0, 1, 2],
            "HR": [80, 85, 90],
            "Resp": [18, 18, 19],
            "O2Sat": [98, 98, 97],
            "Temp": [36.8, 36.9, 37.0],
            "SBP": [0, 100, -5],
            "DBP": [0, 65, 60],
            "target": [0, 0, 0],
        }
    )
    result = engineer_patient_features(patient)
    assert result["shock_index"].iloc[0] == 0.0
    assert result["shock_index"].iloc[1] == 0.85
    assert result["shock_index"].iloc[2] == 0.0


def test_deterministic_output():
    patient = pd.DataFrame(
        {
            "patient_id": ["p1"] * 5,
            "ICULOS": [0, 1, 2, 3, 4],
            "HR": [70, 73, 75, 80, 84],
            "Resp": [16, 17, 18, 18, 19],
            "O2Sat": [98, 97, 97, 96, 95],
            "Temp": [36.8, 36.9, 37.0, 37.0, 37.2],
            "SBP": [120, 116, 114, 110, 108],
            "DBP": [80, 78, 76, 72, 68],
            "target": [0, 0, 0, 1, 1],
        }
    )
    result_a = engineer_patient_features(patient)
    result_b = engineer_patient_features(patient.copy())
    pd.testing.assert_frame_equal(result_a, result_b)


def test_baseline_window_is_documented_configurable():
    assert BASELINE_WINDOW_HOURS == 6
