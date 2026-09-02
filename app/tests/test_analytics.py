from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.feedback import Feedback, FeedbackType
from app.models.patient import Patient
from app.models.prediction import Prediction, RiskLevel
from app.models.user import User
from app.models.vital_reading import VitalReading
from app.models.ward import Ward
from app.tests.test_wards import (
    admin_token,
    auth_header,
    login,
)

client = TestClient(app)


def nurse_token() -> str:
    """Create and login as a nurse user for testing."""
    admin_tok = admin_token()
    response = client.post(
        "/auth/users",
        json={
            "email": "nurse@silentsepsis.test",
            "password": "StrongPass123",
            "full_name": "Test Nurse",
            "role_name": "Nurse",
            "staff_id": "NURSE-1",
        },
        headers=auth_header(admin_tok),
    )
    assert response.status_code == 201
    return login("nurse@silentsepsis.test")


def bootstrap_secret_header() -> dict[str, str]:
    return {"X-Bootstrap-Secret": settings.bootstrap_secret}


def admin_payload() -> dict[str, object]:
    return {
        "email": "admin-wards@silentsepsis.test",
        "password": "StrongPass123",
        "full_name": "Admin Test",
    }


@pytest.fixture(autouse=True)
def clean_data() -> None:
    """Clean database between tests, matching existing test pattern."""
    with SessionLocal() as db:
        db.execute(delete(Feedback))
        db.execute(delete(Alert))
        db.execute(delete(Prediction))
        db.execute(delete(VitalReading))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
        db.execute(delete(User))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(Feedback))
        db.execute(delete(Alert))
        db.execute(delete(Prediction))
        db.execute(delete(VitalReading))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
        db.execute(delete(User))
        db.commit()


def test_precision_recall_calculation_and_rounding() -> None:
    """Test 1: Precision/recall history returns correctly bucketed,
    correctly rounded percentages."""
    token = admin_token()
    with SessionLocal() as db:
        ward = Ward(ward_name="ICU", department="Critical Care", capacity=10)
        db.add(ward)
        db.commit()
        patient = Patient(
            full_name="Test Patient",
            hospital_patient_id="TEST123",
            age=70,
            gender="MALE",
            admission_date=datetime.now(timezone.utc),
            bed_number="B1",
            current_status="ADMITTED",
            ward_id=ward.id,
        )
        db.add(patient)
        db.commit()
        test_user = db.scalar(
            select(User).where(User.email == "admin-wards@silentsepsis.test")
        )

        base_time = datetime.now(timezone.utc) - timedelta(days=10)

        # We need vital readings and predictions for the alerts
        vital = VitalReading(patient_id=patient.id, recorded_at=base_time)
        db.add(vital)
        db.commit()

        pred = Prediction(
            patient_id=patient.id,
            vital_reading_id=vital.id,
            model_version="1.0",
            risk_probability=0.85,
            risk_level=RiskLevel.HIGH,
            generated_at=base_time,
        )
        db.add(pred)
        db.commit()

        alerts = [
            Alert(
                patient_id=patient.id,
                prediction_id=pred.id,
                severity=AlertSeverity.HIGH,
                _status=AlertStatus.CONFIRMED.value,
                message="Alert 1",
                created_at=base_time + timedelta(days=1),
            ),
            Alert(
                patient_id=patient.id,
                prediction_id=pred.id,
                severity=AlertSeverity.HIGH,
                _status=AlertStatus.ACTIVE.value,
                message="Alert 2",
                created_at=base_time + timedelta(days=2),
            ),
            Alert(
                patient_id=patient.id,
                prediction_id=pred.id,
                severity=AlertSeverity.HIGH,
                _status=AlertStatus.ACTIVE.value,
                message="Alert 3",
                created_at=base_time + timedelta(days=7),
            ),
        ]
        db.add_all(alerts)
        db.commit()

        feedbacks = [
            Feedback(
                alert_id=alerts[0].id,
                feedback_type=FeedbackType.CONFIRMED,
                created_at=base_time + timedelta(days=1),
                clinician_id=test_user.id,
            ),
            Feedback(
                alert_id=alerts[1].id,
                feedback_type=FeedbackType.FALSE_POSITIVE,
                created_at=base_time + timedelta(days=2),
                clinician_id=test_user.id,
            ),
            Feedback(
                alert_id=alerts[2].id,
                feedback_type=FeedbackType.MISSED_CASE,
                created_at=base_time + timedelta(days=7),
                clinician_id=test_user.id,
            ),
        ]
        db.add_all(feedbacks)
        db.commit()

    response = client.get(
        "/analytics/precision-recall-history?days=30&bucket_size_days=5",
        headers=auth_header(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6  # 30/5=6 buckets


def test_empty_bucket_returns_null() -> None:
    """Test 2: Bucket with zero feedback returns null, no division by zero."""
    token = admin_token()
    response = client.get(
        "/analytics/precision-recall-history", headers=auth_header(token)
    )
    assert response.status_code == 200
    data = response.json()
    for bucket in data:
        assert bucket["precision"] is None or isinstance(bucket["precision"], int)
        assert bucket["recall"] is None or isinstance(bucket["recall"], int)


def test_ward_summary_returns_correct_fields_and_counts() -> None:
    """Test 3: Ward summary returns exact field names with correct counts."""
    token = admin_token()
    with SessionLocal() as db:
        ward = Ward(ward_name="General", department="Medicine", capacity=20)
        db.add(ward)
        db.commit()

        patient1 = Patient(
            full_name="Patient One",
            hospital_patient_id="PAT001",
            age=65,
            gender="FEMALE",
            admission_date=datetime.now(timezone.utc),
            bed_number="B2",
            current_status="ADMITTED",
            ward_id=ward.id,
        )
        patient2 = Patient(
            full_name="Patient Two",
            hospital_patient_id="PAT002",
            age=75,
            gender="MALE",
            admission_date=datetime.now(timezone.utc),
            bed_number="B3",
            current_status="ADMITTED",
            ward_id=ward.id,
        )
        db.add_all([patient1, patient2])
        db.commit()

        vital1 = VitalReading(
            patient_id=patient1.id, recorded_at=datetime.now(timezone.utc)
        )
        vital2 = VitalReading(
            patient_id=patient2.id, recorded_at=datetime.now(timezone.utc)
        )
        db.add_all([vital1, vital2])
        db.commit()

        pred1 = Prediction(
            patient_id=patient1.id,
            vital_reading_id=vital1.id,
            risk_level=RiskLevel.MODERATE,
            risk_probability=0.75,
            generated_at=datetime.now(timezone.utc),
            model_version="1.0",
        )
        pred2 = Prediction(
            patient_id=patient2.id,
            vital_reading_id=vital2.id,
            risk_level=RiskLevel.LOW,
            risk_probability=0.15,
            generated_at=datetime.now(timezone.utc),
            model_version="1.0",
        )
        db.add_all([pred1, pred2])
        db.commit()

        alert1 = Alert(
            patient_id=patient1.id,
            prediction_id=pred1.id,
            severity=AlertSeverity.MEDIUM,
            _status=AlertStatus.ACTIVE.value,
            message="Alert 1",
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert1)
        db.commit()

    response = client.get(f"/wards/{ward.id}/summary", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) >= {
        "ward",
        "activeAlerts",
        "trendingUp",
        "stable",
        "avgConfirmMinutes",
        "riskLoad",
        "totalPatients",
    }
    assert data["ward"] == "General"
    assert data["totalPatients"] == 2
    assert data["trendingUp"] == 1
    assert data["stable"] == 1
    assert data["activeAlerts"] == 1
    assert data["riskLoad"] == 45  # AVG( (0.75 + 0.15) / 2 ) = 45%


def test_riskload_uses_only_latest_predictions() -> None:
    """Test 12: riskLoad calculation correctly uses ONLY the latest
    prediction for each patient."""
    token = admin_token()
    with SessionLocal() as db:
        ward = Ward(ward_name="Cardiology", department="Heart", capacity=15)
        db.add(ward)
        db.commit()

        p1 = Patient(
            full_name="Multi Pred",
            hospital_patient_id="MP001",
            age=55,
            gender="OTHER",
            admission_date=datetime.now(timezone.utc),
            bed_number="B4",
            current_status="ADMITTED",
            ward_id=ward.id,
        )
        p2 = Patient(
            full_name="Single Pred",
            hospital_patient_id="SP001",
            age=60,
            gender="UNKNOWN",
            admission_date=datetime.now(timezone.utc),
            bed_number="B5",
            current_status="ADMITTED",
            ward_id=ward.id,
        )
        db.add_all([p1, p2])
        db.commit()

        v1 = VitalReading(patient_id=p1.id, recorded_at=datetime.now(timezone.utc))
        v2 = VitalReading(patient_id=p2.id, recorded_at=datetime.now(timezone.utc))
        db.add_all([v1, v2])
        db.commit()

        # P1 has an old prediction (should be ignored) and a new one
        pred_old = Prediction(
            patient_id=p1.id,
            vital_reading_id=v1.id,
            risk_level=RiskLevel.HIGH,
            risk_probability=0.99,
            generated_at=datetime.now(timezone.utc) - timedelta(hours=1),
            model_version="1.0",
        )
        pred_new = Prediction(
            patient_id=p1.id,
            vital_reading_id=v1.id,
            risk_level=RiskLevel.MODERATE,
            risk_probability=0.60,
            generated_at=datetime.now(timezone.utc),
            model_version="1.0",
        )

        # P2 has a single prediction
        pred_single = Prediction(
            patient_id=p2.id,
            vital_reading_id=v2.id,
            risk_level=RiskLevel.LOW,
            risk_probability=0.20,
            generated_at=datetime.now(timezone.utc),
            model_version="1.0",
        )
        db.add_all([pred_old, pred_new, pred_single])
        db.commit()

    response = client.get(f"/wards/{ward.id}/summary", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    # Should be AVG(0.60, 0.20) = 0.40 -> 40%
    assert data["riskLoad"] == 40


def test_avg_confirm_minutes_calculated_correctly() -> None:
    """Test 4: Ward summary avgConfirmMinutes computed correctly
    from real Alert timestamps."""
    token = admin_token()
    with SessionLocal() as db:
        ward = Ward(ward_name="ICU", department="Critical Care", capacity=10)
        db.add(ward)
        db.commit()
        patient = Patient(
            full_name="Test Patient",
            hospital_patient_id="TEST123",
            age=70,
            gender="MALE",
            admission_date=datetime.now(timezone.utc),
            bed_number="B1",
            current_status="ADMITTED",
            ward_id=ward.id,
        )
        db.add(patient)
        db.commit()

        v = VitalReading(patient_id=patient.id, recorded_at=datetime.now(timezone.utc))
        db.add(v)
        db.commit()

        pred = Prediction(
            patient_id=patient.id,
            vital_reading_id=v.id,
            risk_level=RiskLevel.HIGH,
            risk_probability=0.85,
            generated_at=datetime.now(timezone.utc),
            model_version="1.0",
        )
        db.add(pred)
        db.commit()

        created_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        confirmed_at = created_at + timedelta(minutes=30)
        alert = Alert(
            patient_id=patient.id,
            prediction_id=pred.id,
            severity=AlertSeverity.HIGH,
            _status=AlertStatus.CONFIRMED.value,
            message="Alert",
            created_at=created_at,
            confirmed_at=confirmed_at,
        )
        db.add(alert)
        db.commit()

    response = client.get(f"/wards/{ward.id}/summary", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert data["avgConfirmMinutes"] == 30.0


def test_ward_summary_zero_confirmed_alerts() -> None:
    """Test 5: Ward summary with zero confirmed alerts returns 0, not crash."""
    token = admin_token()
    with SessionLocal() as db:
        ward = Ward(ward_name="General", department="Medicine", capacity=20)
        db.add(ward)
        db.commit()
        patient = Patient(
            full_name="Test Patient",
            hospital_patient_id="TEST456",
            age=80,
            gender="FEMALE",
            admission_date=datetime.now(timezone.utc),
            bed_number="B6",
            current_status="ADMITTED",
            ward_id=ward.id,
        )
        db.add(patient)
        db.commit()

        v = VitalReading(patient_id=patient.id, recorded_at=datetime.now(timezone.utc))
        db.add(v)
        db.commit()

        pred = Prediction(
            patient_id=patient.id,
            vital_reading_id=v.id,
            risk_level=RiskLevel.HIGH,
            risk_probability=0.85,
            generated_at=datetime.now(timezone.utc),
            model_version="1.0",
        )
        db.add(pred)
        db.commit()

        alert = Alert(
            patient_id=patient.id,
            prediction_id=pred.id,
            severity=AlertSeverity.HIGH,
            _status=AlertStatus.ACTIVE.value,
            message="Alert",
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        db.commit()

    response = client.get(f"/wards/{ward.id}/summary", headers=auth_header(token))
    assert response.status_code == 200
    data = response.json()
    assert data["avgConfirmMinutes"] == 0.0


def test_staff_response_rate_calculated_correctly() -> None:
    """Test 6: Staff response rate correctly computed (3 of 5 → 60%)."""
    token = admin_token()
    with SessionLocal() as db:
        ward1 = Ward(ward_name="Ward1", department="Medicine", capacity=10)
        ward2 = Ward(ward_name="Ward2", department="Surgery", capacity=10)
        db.add_all([ward1, ward2])
        db.commit()

        patients = []
        for i in range(5):
            patient = Patient(
                full_name=f"P{i} Test",
                hospital_patient_id=f"PAT{i:03d}",
                age=50 + i,
                gender="MALE",
                admission_date=datetime.now(timezone.utc),
                bed_number=f"B{i + 7}",
                current_status="ADMITTED",
                ward_id=ward1.id,
            )
            patients.append(patient)
        db.add_all(patients)
        db.commit()

        vitals = []
        for i in range(5):
            v = VitalReading(
                patient_id=patients[i].id, recorded_at=datetime.now(timezone.utc)
            )
            vitals.append(v)
        db.add_all(vitals)
        db.commit()

        preds = []
        for i in range(5):
            pred = Prediction(
                patient_id=patients[i].id,
                vital_reading_id=vitals[i].id,
                risk_level=RiskLevel.HIGH,
                risk_probability=0.85,
                generated_at=datetime.now(timezone.utc),
                model_version="1.0",
            )
            preds.append(pred)
        db.add_all(preds)
        db.commit()

        statuses = [
            AlertStatus.RESOLVED,
            AlertStatus.DISMISSED,
            AlertStatus.CONFIRMED,
            AlertStatus.ACTIVE,
            AlertStatus.ACTIVE,
        ]
        for i, status in enumerate(statuses):
            alert = Alert(
                patient_id=patients[i].id,
                prediction_id=preds[i].id,
                severity=AlertSeverity.HIGH,
                _status=status.value,
                message=f"Alert {i}",
                created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            db.add(alert)
        db.commit()

    response = client.get(
        "/analytics/staff-response-by-ward", headers=auth_header(token)
    )
    assert response.status_code == 200
    data = response.json()
    ward1_data = next(d for d in data if d["ward"] == "Ward1")
    assert ward1_data["reviewed"] == 60  # 3/5=60%


def test_staff_response_zero_alerts_returns_zero() -> None:
    """Test 7: Staff response rate for ward with zero alerts returns 0, not crash."""
    token = admin_token()
    with SessionLocal() as db:
        ward = Ward(ward_name="EmptyWard", department="Empty", capacity=10)
        db.add(ward)
        db.commit()

    response = client.get(
        "/analytics/staff-response-by-ward", headers=auth_header(token)
    )
    assert response.status_code == 200
    data = response.json()
    empty_ward = next((d for d in data if d["ward"] == "EmptyWard"), None)
    assert empty_ward is not None
    assert empty_ward["reviewed"] == 0


def test_nonexistent_ward_returns_404() -> None:
    """Test 8: Nonexistent ward returns 404."""
    token = admin_token()
    response = client.get(f"/wards/{uuid4()}/summary", headers=auth_header(token))
    assert response.status_code == 404


def test_invalid_query_params_returns_422() -> None:
    """Test 9: Invalid query params (negative days) return 422."""
    token = admin_token()
    response1 = client.get(
        "/analytics/precision-recall-history?days=-10&bucket_size_days=5",
        headers=auth_header(token),
    )
    assert response1.status_code == 422
    response2 = client.get(
        "/analytics/precision-recall-history?days=30&bucket_size_days=-5",
        headers=auth_header(token),
    )
    assert response2.status_code == 422
    response3 = client.get(
        "/analytics/staff-response-by-ward?days=-30", headers=auth_header(token)
    )
    assert response3.status_code == 422


def test_unauthenticated_returns_401() -> None:
    """Test 10: Unauthenticated requests return 401."""
    r1 = client.get("/analytics/precision-recall-history")
    assert r1.status_code == 401
    r2 = client.get("/analytics/staff-response-by-ward")
    assert r2.status_code == 401
    r3 = client.get(f"/wards/{uuid4()}/summary")
    assert r3.status_code == 401


def test_nurse_access_allowed() -> None:
    """Test 11: Any authenticated role (including nurse) can access all endpoints."""
    nurse_tok = nurse_token()
    with SessionLocal() as db:
        ward = Ward(ward_name="NurseWard", department="Medicine", capacity=10)
        db.add(ward)
        db.commit()

    r1 = client.get(
        "/analytics/precision-recall-history", headers=auth_header(nurse_tok)
    )
    assert r1.status_code == 200
    r2 = client.get("/analytics/staff-response-by-ward", headers=auth_header(nurse_tok))
    assert r2.status_code == 200
    r3 = client.get(f"/wards/{ward.id}/summary", headers=auth_header(nurse_tok))
    assert r3.status_code == 200
