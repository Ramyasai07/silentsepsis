from datetime import datetime
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.ml.base import FeatureContribution, PredictionResult, RiskPredictor
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.feedback import Feedback
from app.models.patient import Patient
from app.models.patient_baseline import PatientBaseline
from app.models.prediction import Prediction
from app.models.prediction_feature import PredictionFeature
from app.models.user import User
from app.models.vital_reading import VitalReading
from app.models.ward import Ward

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def migrate_database() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(autouse=True)
def clean_data() -> None:
    with SessionLocal() as db:
        db.execute(delete(Feedback))
        db.execute(delete(AuditLog))
        db.execute(delete(Alert))
        db.execute(delete(PredictionFeature))
        db.execute(delete(Prediction))
        db.execute(delete(VitalReading))
        db.execute(delete(PatientBaseline))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
        db.execute(delete(User))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(Feedback))
        db.execute(delete(AuditLog))
        db.execute(delete(Alert))
        db.execute(delete(PredictionFeature))
        db.execute(delete(Prediction))
        db.execute(delete(VitalReading))
        db.execute(delete(PatientBaseline))
        db.execute(delete(Patient))
        db.execute(delete(Ward))
        db.execute(delete(User))
        db.commit()


def bootstrap_secret_header(value: str | None = None) -> dict[str, str]:
    return {"X-Bootstrap-Secret": value or settings.bootstrap_secret}


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def user_payload(role_name: str, email: str, staff_id: str) -> dict[str, str]:
    return {
        "email": email,
        "staff_id": staff_id,
        "full_name": f"{role_name} User",
        "password": "StrongPass123",
        "role_name": role_name,
    }


def login(email: str, password: str = "StrongPass123") -> dict[str, str]:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def bootstrap_admin() -> str:
    response = client.post(
        "/auth/bootstrap",
        json=user_payload(
            "Admin",
            "admin@silentsepsis.test",
            "ADM-001",
        ),
        headers=bootstrap_secret_header(),
    )
    if response.status_code == 201:
        return login("admin@silentsepsis.test")["access_token"]
    assert response.status_code == 403
    return login("admin@silentsepsis.test")["access_token"]


def create_user(admin_token: str, role_name: str) -> dict[str, object]:
    unique = uuid4().hex[:8]
    response = client.post(
        "/auth/users",
        json=user_payload(
            role_name,
            f"{role_name.lower()}-{unique}@silentsepsis.test",
            f"{role_name[:3].upper()}-{unique}",
        ),
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201
    return response.json()


def create_ward(token: str, capacity: int = 2) -> dict[str, object]:
    response = client.post(
        "/wards",
        json={"name": f"ICU-{uuid4().hex[:6]}", "capacity": capacity},
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def create_patient(token: str, ward_id: UUID, bed_number: str = "A1") -> dict[str, object]:
    response = client.post(
        "/patients",
        json={
            "name": "Audit Patient",
            "age": 50,
            "sex": "FEMALE",
            "ward_id": str(ward_id),
            "bed_number": bed_number,
            "admission_date": "2026-08-07T08:00:00Z",
            "admission_reason": "Sepsis observation",
        },
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


def create_vital(token: str, patient_id: UUID) -> dict[str, object]:
    response = client.post(
        f"/patients/{patient_id}/vitals",
        json={
            "heart_rate": 100,
            "respiratory_rate": 24,
            "systolic_bp": 130,
            "diastolic_bp": 90,
            "spo2": 92.0,
            "temperature": 38.0,
            "recorded_at": datetime.now().isoformat(),
        },
        headers=auth_header(token),
    )
    assert response.status_code == 201
    return response.json()


class HighRiskPredictor(RiskPredictor):
    def predict(self, vitals, baseline):
        return PredictionResult(
            risk_score=0.95,
            risk_tier="CRITICAL",
            feature_contributions=[
                FeatureContribution(
                    feature_name="heart_rate",
                    contribution=0.95,
                    feature_value=vitals.heart_rate,
                )
            ],
        )


def create_alert(token: str) -> Alert:
    ward = create_ward(token)
    patient = create_patient(token, UUID(ward["id"]))
    vital = create_vital(token, UUID(patient["id"]))

    from app.services.prediction_service import PredictionService

    with SessionLocal() as db:
        PredictionService(HighRiskPredictor()).generate_prediction(
            db,
            UUID(patient["id"]),
            UUID(vital["id"]),
        )
        alert = db.scalar(select(Alert).where(Alert.patient_id == UUID(patient["id"])))
        assert alert is not None
        return alert


def latest_audit(action: str) -> AuditLog:
    with SessionLocal() as db:
        audit = db.scalar(
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        assert audit is not None
        return audit


def test_successful_login_creates_audit_entry() -> None:
    admin_token = bootstrap_admin()
    admin_user = client.get("/auth/me", headers=auth_header(admin_token)).json()

    audit = latest_audit("login")

    assert str(audit.user_id) == admin_user["id"]
    assert audit.entity == "user"
    assert str(audit.entity_id) == admin_user["id"]
    assert audit.ip_address is None


def test_admin_creating_user_creates_audit_entry() -> None:
    admin_token = bootstrap_admin()
    created = create_user(admin_token, "Physician")

    audit = latest_audit("user_created")

    assert audit.entity == "user"
    assert str(audit.entity_id) == created["id"]


def test_alert_lifecycle_transitions_create_audit_entries() -> None:
    admin_token = bootstrap_admin()
    alert = create_alert(admin_token)

    transitions = [
        ("acknowledge", "alert_acknowledged", None),
        ("confirm", "alert_confirmed", None),
        ("resolve", "alert_resolved", None),
    ]
    for endpoint, action, payload in transitions:
        response = client.patch(
            f"/alerts/{alert.id}/{endpoint}",
            json=payload,
            headers=auth_header(admin_token),
        )
        assert response.status_code == 200
        audit = latest_audit(action)
        assert audit.entity == "alert"
        assert audit.entity_id == alert.id

    alert = create_alert(admin_token)
    response = client.patch(
        f"/alerts/{alert.id}/dismiss",
        json={"reason": "Not clinically relevant"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    audit = latest_audit("alert_dismissed")
    assert audit.entity == "alert"
    assert audit.entity_id == alert.id


def test_feedback_submission_creates_audit_entry() -> None:
    admin_token = bootstrap_admin()
    alert = create_alert(admin_token)

    response = client.post(
        f"/alerts/{alert.id}/feedback",
        json={"feedback_type": "CONFIRMED", "comments": "Confirmed at bedside"},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 201
    audit = latest_audit("feedback_submitted")
    assert audit.entity == "alert"
    assert audit.entity_id == alert.id


def test_manual_risk_evaluation_trigger_creates_audit_entry() -> None:
    admin_token = bootstrap_admin()

    from app.api.v1 import tasks

    class FakeTask:
        id = "task-id-123"

    def fake_delay():
        return FakeTask()

    original_delay = tasks.evaluate_all_active_patients.delay
    tasks.evaluate_all_active_patients.delay = fake_delay
    try:
        response = client.post(
            "/admin/tasks/evaluate-risk",
            headers=auth_header(admin_token),
        )
    finally:
        tasks.evaluate_all_active_patients.delay = original_delay

    assert response.status_code == 202
    assert response.json() == {"task_id": "task-id-123"}
    audit = latest_audit("risk_evaluation_triggered")
    assert audit.entity == "task"
    assert audit.entity_id is None


def test_get_audit_logs_as_admin_filters_by_entity_and_user_id() -> None:
    admin_token = bootstrap_admin()
    created = create_user(admin_token, "Physician")

    response = client.get(
        "/audit-logs",
        params={"entity": "user", "user_id": created["id"]},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json() == []

    response = client.get(
        "/audit-logs",
        params={"entity": "user", "action": "user_created"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert any(item["entity_id"] == created["id"] for item in body)

    response = client.get(
        f"/audit-logs/{body[0]['id']}",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["id"] == body[0]["id"]


def test_non_admin_cannot_access_audit_logs() -> None:
    admin_token = bootstrap_admin()
    nurse = create_user(admin_token, "Nurse")
    nurse_token = login(nurse["email"])["access_token"]

    response = client.get("/audit-logs", headers=auth_header(nurse_token))

    assert response.status_code == 403


def test_nonexistent_audit_log_returns_404() -> None:
    admin_token = bootstrap_admin()

    response = client.get(f"/audit-logs/{uuid4()}", headers=auth_header(admin_token))

    assert response.status_code == 404


def test_audit_write_failure_does_not_break_primary_action(monkeypatch) -> None:
    admin_token = bootstrap_admin()
    alert = create_alert(admin_token)

    def broken_record(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("app.services.audit_service.record_audit_event", broken_record)

    response = client.patch(
        f"/alerts/{alert.id}/acknowledge",
        headers=auth_header(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "watching"
